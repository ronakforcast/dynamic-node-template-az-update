import boto3
import os
import time
import logging
import requests
from requests.exceptions import RequestException, HTTPError
from typing import List, Optional, Dict

# Constants
CASTAI_API_BASE_URL = "https://api.cast.ai/v1/kubernetes/clusters"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def setup_output_directory(output_dir: str) -> None:
    """Ensure the output directory exists."""
    os.makedirs(output_dir, exist_ok=True)
    logging.info("Output directory '%s' created or already exists.", output_dir)

def check_az_state(az: str) -> str:
    """Check the state of a specific AWS availability zone."""
    region = az[:-1]
    logging.info("Checking state for availability zone '%s' in region '%s'.", az, region)
    ec2_client = boto3.client('ec2', region_name=region)
    response = ec2_client.describe_availability_zones(ZoneNames=[az])
    state = response['AvailabilityZones'][0]['State']
    logging.info("Availability zone '%s' is currently in state: %s", az, state)
    return state

def find_available_zone(az_list: List[str], check_interval: int = 10, output_dir: str = "az-availability") -> Optional[str]:
    """
    Check a list of AWS availability zones and return the first available zone.
    """
    setup_output_directory(output_dir)
    logging.info("Starting to check availability zones from the provided list: %s", az_list)
    
    while True:
        for az in az_list:
            state = check_az_state(az)
            
            # Write state to a file for record-keeping
            with open(os.path.join(output_dir, az), 'w') as f:
                f.write(state)
            
            logging.info("State of availability zone '%s' has been recorded.", az)
            if state == "available":
                logging.info("Available zone found: %s", az)
                return az
        
        logging.warning("No available zones found. Retrying after %d seconds...", check_interval)
        time.sleep(check_interval)

def get_node_templates(api_key: str, cluster_id: str) -> List[Dict]:
    """Fetches node templates for a given cluster ID."""
    url = f"{CASTAI_API_BASE_URL}/{cluster_id}/node-templates?includeDefault=true"
    headers = {
        'X-API-Key': api_key,
        'accept': 'application/json'
    }

    logging.info("Fetching node templates for cluster ID: %s", cluster_id)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        node_templates = response.json().get('items', [])
        logging.info("Successfully retrieved %d node templates for cluster ID %s.", len(node_templates), cluster_id)
        return node_templates
    except (HTTPError, RequestException, ValueError) as err:
        logging.error("Error fetching node templates for cluster %s: %s", cluster_id, err)
    return []

def update_node_template(api_key: str, cluster_id: str, node_template_name: str, 
                         node_template: Dict, current_active_az: List[str]) -> Optional[Dict]:
    """
    Updates a specific node template's constraints for availability zones.
    """
    url = f"{CASTAI_API_BASE_URL}/{cluster_id}/node-templates/{node_template_name}"
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }

    logging.info("Attempting to update node template '%s' for cluster '%s' with new AZ constraints: %s",
                 node_template_name, cluster_id, current_active_az)

    try:
        node_template['template']['constraints']['azs'] = current_active_az
        response = requests.put(url, headers=headers, json=node_template['template'])
        response.raise_for_status()
        logging.info("Successfully updated node template '%s' for cluster '%s'.", node_template_name, cluster_id)
        return response.json()
    except (HTTPError, RequestException, ValueError) as err:
        logging.error("Error updating template '%s' in cluster '%s': %s", node_template_name, cluster_id, err)
    return None

def process_clusters(api_key: str, cluster_id: str, node_template_names: List[str], current_active_az: List[str]) -> None:
    """
    Processes the clusters and updates node templates based on provided criteria.
    """
    logging.info("Starting to process cluster ID: %s", cluster_id)
    
    node_templates = get_node_templates(api_key, cluster_id)
    if not node_templates:
        logging.warning("No node templates found for cluster ID %s. Skipping update.", cluster_id)
        return

    for node_template in node_templates:
        node_template_data = node_template['template']
        node_template_name = node_template_data['name']
        node_az_constraints = node_template_data['constraints'].get('azs', [])

        logging.info("Evaluating node template '%s' with current AZ constraints: %s", node_template_name, node_az_constraints)

        if node_template_name in node_template_names:
            if len(node_az_constraints) == 1 and node_az_constraints[0] == current_active_az[0]:
                logging.info("Skipping update for '%s' as AZ constraints already match current active AZ.", node_template_name)
                continue

            logging.info("Conditions met for updating node template '%s'. Proceeding with update.", node_template_name)
            if update_node_template(api_key, cluster_id, node_template_name, node_template, current_active_az):
                logging.debug("Node template '%s' updated successfully in cluster '%s'.", node_template_name, cluster_id)
                logging.info("sleeping 5 sec before next api call")
                time.sleep(5)
            else:
                logging.error("Failed to update node template '%s' in cluster '%s'.", node_template_name, cluster_id)

def main():

    try:
        api_key = os.getenv("API_KEY")
        cluster_id = os.getenv("CLUSTER_ID")
        node_template_names = os.getenv("NODE_TEMPLATE_NAMES").split(",")
        az_list = os.getenv("AZ_LIST").split(",")
        
        if not all([api_key, cluster_id, node_template_names, az_list]):
            raise ValueError("One or more required environment variables are missing.")

        logging.info("Environment variables successfully loaded.")
    except ValueError as e:
        logging.error("Error loading environment variables: %s", e)
        return

    logging.info("Starting the script with Cluster ID: %s, Node Template Names: %s, AZ List: %s",
                 cluster_id, node_template_names, az_list)

    while True:
        current_active_az = []
        available_zone = find_available_zone(az_list)
        if available_zone:
            current_active_az = [available_zone]
            logging.info("Active availability zone found: %s", available_zone)
        else:
            logging.warning("No available zone found, no updates will proceed in this cycle.")

        process_clusters(api_key, cluster_id, node_template_names, current_active_az)
        logging.info("Processing cycle complete. Sleeping for 60 seconds before the next cycle.")
        time.sleep(60)

if __name__ == "__main__":
    main()