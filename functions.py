import json
import os
from prompts import assistant_instructions
import pandas as pd

def get_tires(width=None, height=None, diameter=None, season=None, vehicle=None, minimum_price=None, maximum_price=None):

    df = pd.read_excel("product_catalog.xlsx")

    if width is not None:
        df = df[df['width'] == width]
    if height is not None:
        df = df[df['height'] == height]
    if diameter is not None:
        df = df[df['diameter'] == diameter]
    if season is not None:
        df = df[df['season'].str.contains(season, case=False)]
    if vehicle is not None:
        df = df[df['vehicle'].str.contains(vehicle, case=False)]
    if minimum_price is not None:
        df = df[df['price_bgn'] >= minimum_price]
    if maximum_price is not None:
        df = df[df['price_bgn'] <= maximum_price]

    result = df.head(3).to_json(orient='records', date_format='iso')

    result_list = json.loads(result)

    for tire in result_list:
        if tire["image_url"] is not None:
            tire["image_url"] += f"?width={tire['width']}&ratio={tire['height']}&rim={tire['diameter']}"

    result = json.dumps(result_list)

    return result


def create_assistant(client):
    assistant_file_path = 'assistant.json'

    if False and os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            vector_store_id = assistant_data['vector_store_id']
            print("Loaded existing assistant ID.")
    else:
        vector_store = client.beta.vector_stores.create(name="Knowledge about Primex")
        vector_store_id=vector_store.id

        file_paths = ["Q&A.json"]
        file_streams = [open(path, "rb") for path in file_paths]


        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
        )

        #print("Vector store created!")
        #print(file_batch.status)
        #print(file_batch.file_counts)

        assistant = client.beta.assistants.create(
            instructions=assistant_instructions,
            model="gpt-4o",
            tools=[{
                "type": "file_search",
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tires",
                    "description": "Get tire models based on parameters such as size, season, vehicle type, and price range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "width": {
                                "type": "integer",
                                "description": "The width of the tire in millimeters (e.g., 205)."
                            },
                            "height": {
                                "type": "integer",
                                "description": "The height of the tire's sidewall as a percentage of the tire's width (e.g., 55)."
                            },
                            "diameter": {
                                "type": "integer",
                                "description": "The diameter of the wheel in inches (e.g., 16)."
                            },
                            "season": {
                                "type": "string",
                                "enum": ["Winter", "Summer", "All-season"],
                                "description": "The season for the tire: winter, summer, or all-season."
                            },
                            "vehicle": {
                                "type": "string",
                                "enum": ["4x4", "van", "car"],
                                "description": "The type of vehicle the tire is for: 4x4, van, or car."
                            },
                            "minimum_price": {
                                "type": "integer",
                                "description": "The minimum price the client is willing to pay for a tire in leva."
                            },
                            "maximum_price": {
                                "type": "integer",
                                "description": "The maximum price the client is willing to pay for a tire in leva."
                            }
                        },
                        "required": ["width", "height", "diameter","vehicle"] #, "season", "minimum_price", "maximum_price"]
                    }
                }
            },
            ],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )

        with open(assistant_file_path, 'w') as file:
            IDs = {
                'assistant_id': assistant.id,
                'vector_store_id': vector_store_id
            }
            json.dump(IDs, file)

        assistant_id = assistant.id

    return assistant_id, vector_store_id
