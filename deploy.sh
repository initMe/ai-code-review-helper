#!/bin/bash

# 配置变量
IMAGE_NAME="code-review-helper"
TAG="1.0"
CONTAINER_NAME="ai-code-review-helper"

# 从命令行参数获取值
REDIS_HOST=$1
AZURE_OPENAI_API_KEY=$2
GITLAB_INSTANCE_URL=$3

# 如果REDIS_HOST为空，则默认使用127.0.0.1
if [ -z "$REDIS_HOST" ]; then
  REDIS_HOST="127.0.0.1"
fi

# 如果AZURE_OPENAI_API_KEY为空，则默认使用占位符
if [ -z "$AZURE_OPENAI_API_KEY" ]; then
  AZURE_OPENAI_API_KEY="GAYVJeRNwgxqA1ck88xuuyCTGaavjlyUroeXI6xPFRopkihmFOmHJQQJ99BDACHrzpqXJ3w3AAABACOG63NT"
fi

# 如果GITLAB_INSTANCE_URL为空，则默认使用占位符
if [ -z "$GITLAB_INSTANCE_URL" ]; then
  GITLAB_INSTANCE_URL="http://gitlab.midust.com"
fi


echo "🔍 正在停止并删除旧容器..."

# 判断容器是否存在
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
  docker stop $CONTAINER_NAME
  docker rm $CONTAINER_NAME
else
  echo "⚠️ 未找到容器 $CONTAINER_NAME，无需停止和删除。"
fi

echo "🧹 正在删除旧镜像..."

# 判断镜像是否存在
if [ "$(docker images -q $IMAGE_NAME:$TAG)" ]; then
  docker rmi $IMAGE_NAME:$TAG
else
  echo "⚠️ 未找到镜像 $IMAGE_NAME:$TAG，无需删除。"
fi

echo "🔨 开始构建镜像..."
docker build -t $IMAGE_NAME:$TAG .

docker run -d --restart unless-stopped --privileged --net=host -p 8088:8088 \
  -e ADMIN_API_KEY="code123456" \
  -e AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY \
  -e REDIS_HOST=$REDIS_HOST \
  -e REDIS_PASSWORD="xvhcnIK24cfm8v#MMJQS" \
  -e REDIS_SSL_ENABLED=false \
  -e REDIS_DB=0 \
  -e GITLAB_INSTANCE_URL=$GITLAB_INSTANCE_URL \
  -e CUSTOM_WEBHOOK_URL="https://oapi.dingtalk.com/robot/send?access_token=34208528cceefaa2c6871d09119cbf3d6959ecd178b5efb6db61e115e8546a32" \
  --name $CONTAINER_NAME \
  $IMAGE_NAME:$TAG

echo "✅ 部署完成，容器正在运行："
docker ps | grep $CONTAINER_NAME