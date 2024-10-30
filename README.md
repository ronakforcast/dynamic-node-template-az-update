# dynamic-node-template-az-update

Dynamic AZ Sync is a Python application that automates the process of checking the availability of AWS Availability Zones (AZs) and updates Kubernetes node templates accordingly. The application integrates with the CAST AI API to manage node templates based on the state of the AZs.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Deployment](#deployment)
- [Usage](#usage)
- [Environment Variables](#environment-variables)
- [Logging](#logging)


## Features

- Check the availability of specified AWS Availability Zones.
- Update Kubernetes node templates in real-time based on AZ availability.
- Logs detailed information about the process for monitoring and debugging.

## Requirements (added in DockerFile)

- Python 3.7 or higher
- `boto3` library for AWS SDK
- `requests` library for making HTTP requests
- Access to CAST AI API with valid credentials

### IAM Role for Worker Nodes

The IAM role attached to worker nodes must have `ec2:DescribeAvailabilityZones` permissions. Below is an example IAM policy that grants the necessary permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ec2:DescribeAvailabilityZones",
      "Resource": "*"
    }
  ]
}
```

## Deployment

This application is deployed as a Kubernetes Deployment. Below is a sample YAML configuration to deploy the application:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamicazsync-deployment
  labels:
    app: dynamicazsync
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dynamicazsync
  template:
    metadata:
      labels:
        app: dynamicazsync
    spec:
      containers:
      - name: dynamicazsync
        image: ronakpatildocker/dynamicazsync:latest
        ports:
        - containerPort: 80
        env:
          - name: API_KEY
            value: ""  # Replace with your API Key
          - name: CLUSTER_ID
            value: ""  # Replace with your cluster ID
          - name: NODE_TEMPLATE_NAMES
            value: "testNT1,testNT2"  # Comma-separated list of node template names
          - name: AZ_LIST
            value: "us-east-2a,us-east-2b,us-east-2c"  # Comma-separated AZs by priority order
```

## Usage

1. **Deploy to Kubernetes**: Apply the above YAML configuration to your Kubernetes cluster.

    ```bash
    kubectl apply -f deployment.yaml
    ```

2. **Monitor Logs**: You can check the logs of the deployment using:

    ```bash
    kubectl logs -f deployment/dynamicazsync-deployment
    ```

## Environment Variables

The application requires the following environment variables to be set:

- `API_KEY`: Your CAST AI API key.
- `CLUSTER_ID`: The ID of your Kubernetes cluster.
- `NODE_TEMPLATE_NAMES`: A comma-separated list of node template names to be updated.
- `AZ_LIST`: A comma-separated list of AWS availability zones to check.

## Logging

The application logs various events and errors, making it easier to monitor its execution. Logs are output to the standard output, which can be viewed via the Kubernetes logs.


