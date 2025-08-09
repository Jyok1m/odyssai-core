from typing import Dict, Union, List


def check_empty_fields(
    data: Dict[str, Union[str, int]],
    required_fields: List[str],
) -> Dict[str, Union[bool, str, List[str]]]:
    empty_fields = [field for field in required_fields if not data.get(field)]
    if empty_fields:
        return {
            "result": False,
            "error": "Missing or empty fields",
            "empty_fields": empty_fields,
        }
    return {"result": True}
