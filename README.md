# Censo Municipal de Animales

Aplicación web para la gestión del padrón municipal de animales.

## Estructura

```
├── docker-compose.yml   # Orquestación de todos los servicios
├── nginx.conf           # Configuración del servidor web
├── web/
│   └── index.html       # Interfaz de usuario
└── api/
    ├── Dockerfile       # Imagen del backend Flask
    ├── requirements.txt
    └── app.py           # API REST
```

## Arrancar

```bash
docker-compose up -d --build
```

La aplicación queda disponible en http://<IP-DEL-SERVIDOR>

## Parar

```bash
docker-compose down
```

## Variables de entorno (api)

| Variable      | Valor por defecto |
|---------------|-------------------|
| DB_HOST       | mariadb           |
| DB_PORT       | 3306              |
| DB_USER       | root              |
| DB_PASSWORD   | 123               |
| DB_NAME       | censo_animales    |
