app/
├── **init**.py
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
│
├── core/
│ ├── **init**.py
│ ├── config.py
│ ├── database.py
│ ├── security.py
│ ├── storage.py
│ ├── dependencies.py
│ └── exceptions.py
│
├── domain/
│ ├── **init**.py
│ ├── models/
│ │ ├── **init**.py
│ │ ├── user.py
│ │ ├── session.py
│ │ ├── token.py
│ │ └── file.py
│ ├── schemas/
│ │ ├── **init**.py
│ │ ├── auth.py
│ │ ├── user.py
│ │ └── file.py
│ └── repositories/
│ ├── **init**.py
│ ├── user_repository.py
│ ├── session_repository.py
│ └── file_repository.py
│
├── application/
│ ├── **init**.py
│ ├── services/
│ │ ├── **init**.py
│ │ ├── auth_service.py
│ │ ├── user_service.py
│ │ └── file_service.py
│ └── use_cases/
│ ├── **init**.py
│ ├── authenticate_user.py
│ └── upload_avatar.py
│
├── api/
│ ├── **init**.py
│ ├── dependencies.py
│ ├── middlewares.py
│ ├── errors.py
│ └── v1/
│ ├── **init**.py
│ └── routers/
│ ├── **init**.py
│ ├── auth.py
│ ├── users.py
│ ├── profile.py
│ ├── files.py
│ └── admin.py
│
├── utils/
│ ├── **init**.py
│ ├── image_processor.py
│ ├── validators.py
│ ├── logger.py
│ └── helpers.py
│
└── scripts/
├── **init**.py
└── init_db.py
