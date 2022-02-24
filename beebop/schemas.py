import json


def read_schema(name):
    with open('spec/'+name+'.schema.json', 'r', encoding="utf-8") as file:
        schema_data = file.read()
    schema = json.loads(schema_data)
    return schema


class Schema:
    def __init__(self):
        self.version = read_schema("version")
        # add new schemas here
