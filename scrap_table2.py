import json
import uuid
import boto3
import requests


def lambda_handler(event, context):
    # Endpoint directo de la API del IGP para reportes sismicos
    # (reemplaza la consulta HTML estatica que no contiene la tabla renderizada)
    url = "https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/2026"

    headers_req = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers_req, timeout=10)
        if response.status_code != 200:
            return {
                "statusCode": response.status_code,
                "body": json.dumps(
                    {"message": "Error al acceder a los datos del IGP"}
                ),
            }

        sismos_data = response.json()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error en la petición: {str(e)}"}),
        }

    # Seleccionar únicamente los 10 últimos sismos reportados
    ultimos_10_sismos = sismos_data[:10]

    # Conectar a DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("TablaWebScrapping")

    # Limpiar elementos antiguos de la tabla DynamoDB
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan.get("Items", []):
            batch.delete_item(Key={"id": item["id"]})

    # Preparar e insertar los 10 registros
    items_guardados = []
    for index, sismo in enumerate(ultimos_10_sismos, start=1):
        item = {
            "id": str(uuid.uuid4()),
            "#": index,
            "fecha_utc": str(sismo.get("fecha_utc", "")).strip(),
            "fecha_local": str(sismo.get("fecha_local", "")).strip(),
            "magnitud": str(sismo.get("magnitud", "")).strip(),
            "profundidad": str(sismo.get("profundidad", "")).strip(),
            "latitud": str(sismo.get("latitud", "")).strip(),
            "longitud": str(sismo.get("longitud", "")).strip(),
            "referencia": str(sismo.get("referencia", "")).strip(),
        }

        table.put_item(Item=item)
        items_guardados.append(item)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(items_guardados, ensure_ascii=False),
    }