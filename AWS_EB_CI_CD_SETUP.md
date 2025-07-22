# AWS Elastic Beanstalk CI/CD with GitHub Actions for `fast-api-ebs-poc`

This guide provides end-to-end instructions for deploying your FastAPI Docker app to AWS Elastic Beanstalk using GitHub Actions, supporting `dev`, `staging`, and `prod` environments.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [IAM User Setup](#iam-user-setup)
3. [S3 Bucket Naming & Setup](#s3-bucket-naming--setup)
4. [Elastic Beanstalk Environment Setup](#elastic-beanstalk-environment-setup)
5. [Manual vs Automated Provisioning](#manual-vs-automated-provisioning)
6. [GitHub Secrets Configuration](#github-secrets-configuration)
7. [GitHub Actions Workflow](#github-actions-workflow)
8. [Custom Domain & SSL (Optional)](#custom-domain--ssl-optional)
9. [Rollback & Versioning](#rollback--versioning)
10. [Future Enhancements](#future-enhancements)

---

## Prerequisites
- AWS account
- GitHub repository for your project
- Dockerfile in your project root
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed locally (for manual provisioning)

---

## IAM User Setup
1. **Create an IAM user** with programmatic access.
2. Attach the following policies:
   - `AWSElasticBeanstalkFullAccess`
   - `AmazonS3FullAccess` (or restrict to your S3 buckets)
   - `AmazonEC2ContainerRegistryFullAccess` (if using ECR)
3. Save the **Access Key ID** and **Secret Access Key** for GitHub secrets.

---

## S3 Bucket Naming & Setup
- S3 bucket pattern: `fast-api-ebs-poc-{env}` (e.g., `fast-api-ebs-poc-dev`)
- Region: `ap-south-1`

### Manual Setup
For each environment (`dev`, `staging`, `prod`):
```sh
aws s3api create-bucket --bucket fast-api-ebs-poc-dev --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1
# Repeat for staging and prod
```
If the bucket exists, this command will fail safely; you can ignore the error.

### Automated Setup (Optional)
You can add a step in your workflow to check/create the bucket using AWS CLI.

---

## Elastic Beanstalk Environment Setup
- Application name: `fast-api-ebs-poc`
- Environment names: `fast-api-ebs-poc-dev`, `fast-api-ebs-poc-staging`, `fast-api-ebs-poc-prod`
- Platform: **Docker running on 64bit Amazon Linux 2**

### Manual Setup
For each environment:
1. Go to AWS Console → Elastic Beanstalk → Create Application
2. Name: `fast-api-ebs-poc`
3. Environment: `fast-api-ebs-poc-{env}`
4. Platform: Docker
5. Upload a sample Docker image or skip for now
6. Note the environment URL (e.g., `fast-api-ebs-poc-dev.ap-south-1.elasticbeanstalk.com`)

### Automated Setup (Optional)
You can use AWS CLI or CloudFormation for provisioning. See AWS docs for details.

---

## GitHub Secrets Configuration
Add these secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` (set to `ap-south-1`)
- `EB_APP_NAME` (set to `fast-api-ebs-poc`)
- `EB_ENV_DEV` (set to `fast-api-ebs-poc-dev`)
- `EB_ENV_STAGING` (set to `fast-api-ebs-poc-staging`)
- `EB_ENV_PROD` (set to `fast-api-ebs-poc-prod`)
- `S3_BUCKET_DEV` (set to `fast-api-ebs-poc-dev`)
- `S3_BUCKET_STAGING` (set to `fast-api-ebs-poc-staging`)
- `S3_BUCKET_PROD` (set to `fast-api-ebs-poc-prod`)
- Any environment variables your app needs (e.g., `APP_ENV`, `DATABASE_URL`, etc.)

---

## GitHub Actions Workflow
- **Manual trigger** for all environments
- **Any branch** can deploy to `dev`
- **Only `main` branch** can deploy to `staging` and `prod`
- **Runs tests** before deployment
- **Tags Docker images** with branch name
- **Injects environment variables** from secrets
- **Supports rollback** on deployment failure

### Example Workflow: `.github/workflows/deploy-ebs.yml`
```yaml
name: Deploy to AWS Elastic Beanstalk

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment (dev, staging, prod)'
        required: true
        default: 'dev'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: ${{ github.event.inputs.environment }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Run tests
        run: |
          python -m pip install --upgrade pip
          pip install -r requirement-dev.txt
          pytest

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Set environment variables
        run: |
          echo "APP_ENV=${{ github.event.inputs.environment }}" >> $GITHUB_ENV
          # Add more as needed

      - name: Build Docker image
        run: |
          docker build -t fast-api-ebs-poc:${{ github.ref_name }} .

      - name: Zip Dockerrun.aws.json
        run: |
          echo '{
            "AWSEBDockerrunVersion": 1,
            "Image": {
              "Name": "fast-api-ebs-poc:${{ github.ref_name }}",
              "Update": "true"
            },
            "Ports": [
              {"ContainerPort": 8000}
            ]
          }' > Dockerrun.aws.json
          zip deploy.zip Dockerrun.aws.json

      - name: Upload to S3
        run: |
          aws s3 cp deploy.zip s3://${{ secrets['S3_BUCKET_' + env.APP_ENV | upper] }}/deploy-${{ github.sha }}.zip

      - name: Deploy to Elastic Beanstalk
        run: |
          aws elasticbeanstalk create-application-version \
            --application-name ${{ secrets.EB_APP_NAME }} \
            --version-label "${{ github.sha }}" \
            --source-bundle S3Bucket="${{ secrets['S3_BUCKET_' + env.APP_ENV | upper] }}",S3Key="deploy-${{ github.sha }}.zip"
          aws elasticbeanstalk update-environment \
            --environment-name ${{ secrets['EB_ENV_' + env.APP_ENV | upper] }} \
            --version-label "${{ github.sha }}"

      - name: Monitor deployment and rollback on failure
        run: |
          # Add script to monitor deployment status and rollback if needed
          # See AWS CLI docs for eb environment health checks

    if: |
      github.event.inputs.environment == 'dev' ||
      (github.event.inputs.environment != 'dev' && github.ref == 'refs/heads/main')
```

---

## Custom Domain & SSL (Optional)
1. Set up a custom domain in Route 53 or your DNS provider.
2. Point the CNAME to your Elastic Beanstalk environment URL.
3. Use AWS Certificate Manager (ACM) to provision an SSL certificate.
4. Attach the certificate to your Elastic Beanstalk environment via the Load Balancer settings.

---

## Rollback & Versioning
- Elastic Beanstalk keeps previous application versions by default.
- You can rollback via the AWS Console or CLI:
  ```sh
  aws elasticbeanstalk update-environment \
    --environment-name fast-api-ebs-poc-dev \
    --version-label <previous-version-label>
  ```
- The workflow can be extended to automate rollback on failed deployments.

---

## Future Enhancements
- Add database (RDS) or other AWS resources as needed
- Use infrastructure-as-code (CloudFormation, Terraform) for full automation
- Add Slack/email notifications for deployment status
- Add blue/green deployment strategy for zero-downtime releases

---

## References
- [AWS Elastic Beanstalk Docs](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html)
- [GitHub Actions for AWS](https://github.com/aws-actions/)
- [Deploying Docker to Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create_deploy_docker.html) 