# Configure docker build with live-updates
docker_build(
    'auth-service',
    context='.',
    live_update=[
        sync('.', '/app'),
        run(
            'pip install -r /app/requirements.txt  --extra-index-url https://pypi.ehps.ncsu.edu',
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

k8s_yaml(kustomize('.'))

k8s_resource('auth-service', port_forwards='8003:8000', labels=['service'])