load('ext://secret', 'secret_from_dict')
load('ext://dotenv', 'dotenv')
load('ext://namespace', 'namespace_create', 'namespace_inject')
dotenv()
namespace_create('auth-service')

# Configure docker build with live-updates
docker_build(
    'auth-service',
    context='.',
    live_update=[
        sync('.', '/app'),
        run(
            'pip install -r /app/requirements.txt',
            trigger=['./requirements.txt']
       )
    ],
    entrypoint='uvicorn main:app --reload'
)

# Specify k8s manifest
manifest = read_yaml_stream('./k8s/deployment.yml')

# K8s overrides for local dev
for o in manifest:
    o['spec']['template']['spec']['containers'][0]['image'] = 'auth-service'

k8s_yaml(encode_yaml_stream(manifest))

secret_env_map = {
    'google-client-id': 'GOOGLE_CLIENT_ID',
    'jwt-secret': 'JWT_SECRET',
    'mongodb-url': 'MONGODB_URL',
    'api-key': 'API_KEY',
    'mongo-password-id': 'MONGO_PASSWORD_ID',
    'password-api-base-url': 'PASSWORD_API_BASE_URL',
    'password-state-api-key': 'PASSWORD_API_KEY',
    'password-api-list-id': 'PASSWORD_API_LIST_ID',
    'password-title': 'PASSWORD_TITLE',
}

# Load secrets from environment variables
# Load them as YAML
for k, v in secret_env_map.items():
    value = os.getenv(v)
    k8s_yaml(secret_from_dict(
        k, # name of the secret
        'auth-service', # namespace
        inputs={
            'password': value
        }
    ))

k8s_resource('auth-service', port_forwards='8003:8000', labels=['service'])
