VER 1.0

# App

APP_NAME=""
DEBUG=true

# MongoDB

MONGODB_URL
MONGODB_DB_NAME=dtcdb

# JWT

SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_EXPIRE_DAYS_LONG=30

# CORS

BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Cookies

SECURE_COOKIES=false # true in production

VER 1.1

# App

APP_NAME=""
APP_VERSION="1.0.0"
ENVIRONMENT=development
DEBUG=true

# Server

HOST=0.0.0.0
PORT=8000
WORKERS=4

# MongoDB

MONGODB_URL=

# JWT

SECRET_KEY=your-super-secret-jwt-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_EXPIRE_DAYS_LONG=30

# CORS

BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Storage - MinIO (development)

STORAGE_PROVIDER=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_SECURE=
STORAGE_BUCKET=

# Storage - S3 (production)

# STORAGE_PROVIDER=s3

# STORAGE_ENDPOINT=https://s3.amazonaws.com

# STORAGE_ACCESS_KEY=your-aws-access-key

# STORAGE_SECRET_KEY=your-aws-secret-key

# STORAGE_REGION=us-east-1

# STORAGE_BUCKET=xstv-dtc-production

# STORAGE_SECURE=true

# STORAGE_PUBLIC_URL=https://your-bucket.s3.amazonaws.com

# Image Processing

AVATAR_MAX_SIZE_MB=5
AVATAR_ALLOWED_TYPES=["image/jpeg","image/png","image/webp"]
AVATAR_MAX_WIDTH=1024
AVATAR_MAX_HEIGHT=1024
AVATAR_THUMBNAIL_SIZE=256
