FROM satregistry.ehps.ncsu.edu:7001/it/python-image@sha256:a681d9aac60bc0b4ddcf52cc84a3319fb6a9d309acd3cd280122d3f060e18d1d

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]