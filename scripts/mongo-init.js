// Script de inicialización para MongoDB
db = db.getSiblingDB("admin");

// Crear usuario para la aplicación
db.createUser({
  user: "xstv_user",
  pwd: "xstv_password",
  roles: [
    {
      role: "readWrite",
      db: "xstv_dtc",
    },
  ],
});

// Crear base de datos de la aplicación
db = db.getSiblingDB("xstv_dtc");

// Crear colecciones iniciales
db.createCollection("users");
db.createCollection("sessions");
db.createCollection("token_blacklist");
db.createCollection("files");
db.createCollection("logs");

print("✅ MongoDB initialized successfully");
