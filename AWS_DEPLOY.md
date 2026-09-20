# Deploying to AWS ECS Fargate

Assumes an AWS account with the CLI configured (`aws configure`) and Docker
installed locally. Ships as a single container (API + static frontend).

## 1. Create an ECR repository

```bash
aws ecr create-repository --repository-name chess-coach --region us-east-1
```

## 2. Build and push the image

```bash
cd chesscoach
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1

docker build -t chess-coach -f backend/Dockerfile .

aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker tag chess-coach:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/chess-coach:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/chess-coach:latest
```

## 3. (Optional) Store your Anthropic API key in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name chess-coach/anthropic-api-key \
  --secret-string "sk-ant-your-key-here"
```

Skip this and don't set the env var in the task definition if you'd rather
run purely on the template-based fallback coaching.

## 4. Create the ECS cluster, task definition, and service

Easiest via the ECS console for a first deploy:
1. ECS → Clusters → Create cluster → Fargate
2. Task Definitions → Create new → Fargate → 0.5 vCPU / 1GB memory
   - Container image = the ECR URI from step 2, port mapping = 8000
   - Environment variable `ANTHROPIC_API_KEY` → "ValueFrom" the Secrets Manager ARN (optional)
3. Create Service → Fargate, 1 desired task, public subnet, auto-assign public IP
   - Security group: allow inbound TCP 8000 (or attach an ALB on port 80 → target 8000)

## 5. Confirm it's live

```bash
curl http://<public-ip-or-alb-dns>:8000/api/health
```

## Cost note

A single Fargate task at 0.5 vCPU / 1GB runs roughly $10-15/month continuously.
Scale desired count to 0 when not actively demoing it.
