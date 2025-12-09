app/
├── **init**.py
├── main.py # Punto de entrada
├── config.py # Configuración centralizada
├── requirements.txt
├── .env.example
├── docker-compose.yml # Para desarrollo con MinIO
│
├── core/ # Núcleo de la aplicación
│ ├── **init**.py
│ ├── config.py # Configuración
│ ├── database.py # MongoDB
│ ├── security.py # JWT, hashing
│ ├── storage.py # S3/MinIO client
│ ├── dependencies.py # Dependencias FastAPI
│ └── exceptions.py # Excepciones personalizadas
│
├── domain/ # Lógica de negocio
│ ├── **init**.py
│ ├── models/ # Modelos Pydantic
│ │ ├── **init**.py
│ │ ├── user.py
│ │ ├── session.py
│ │ ├── token.py
│ │ └── file.py
│ │
│ ├── schemas/ # Esquemas para request/response
│ │ ├── **init**.py
│ │ ├── auth.py
│ │ ├── user.py
│ │ └── file.py
│ │
│ └── repositories/ # Acceso a datos
│ ├── **init**.py
│ ├── user_repository.py
│ ├── session_repository.py
│ └── file_repository.py
│
├── application/ # Casos de uso
│ ├── **init**.py
│ ├── services/
│ │ ├── **init**.py
│ │ ├── auth_service.py
│ │ ├── user_service.py
│ │ └── file_service.py
│ │
│ └── use_cases/
│ ├── **init**.py
│ ├── authenticate_user.py
│ ├── upload_avatar.py
│ └── update_profile.py
│
├── api/ # Capa de presentación
│ ├── **init**.py
│ ├── dependencies.py # Dependencias de rutas
│ ├── middlewares.py # Middlewares
│ ├── errors.py # Handlers de errores
│ │
│ └── v1/ # Versión 1 de la API
│ ├── **init**.py
│ ├── routers/
│ │ ├── **init**.py
│ │ ├── auth.py
│ │ ├── users.py
│ │ ├── profile.py
│ │ └── files.py
│ │
│ └── endpoints/
│ ├── **init**.py
│ ├── auth.py
│ ├── users.py
│ └── files.py
│
├── infrastructure/ # Conexiones externas
│ ├── **init**.py
│ ├── minio_client.py # Cliente MinIO
│ ├── s3_client.py # Cliente S3
│ └── email_client.py # Cliente email
│
├── utils/ # Utilidades
│ ├── **init**.py
│ ├── image_processor.py # Procesamiento de imágenes
│ ├── validators.py # Validadores
│ ├── logger.py # Logging configurado
│ └── helpers.py # Funciones auxiliares
│
├── tests/ # Tests
│ ├── **init**.py
│ ├── conftest.py
│ ├── unit/
│ └── integration/
│
└── scripts/ # Scripts de utilidad
├── **init**.py
├── init_db.py
└── backup.py
