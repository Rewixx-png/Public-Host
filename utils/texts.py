# utils/texts.py
import json

class TextMessages:
    def __init__(self, file_path="texts.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Text file not found at {file_path}")
            self.data = {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}")
            self.data = {}

    def get(self, key: str, **kwargs) -> str:
        """
        Получает текст по ключу и форматирует его с переданными аргументами.
        Ключи могут быть вложенными, разделенными точкой.
        Пример: texts.get("account.title", user_id=123, balance=100)
        """
        try:
            # Навигация по вложенным ключам
            value = self.data
            for k in key.split('.'):
                value = value[k]
            
            # Форматирование строки, если переданы аргументы
            if kwargs:
                return value.format(**kwargs)
            return value
        except KeyError:
            # Возвращаем заметное сообщение об ошибке, если ключ не найден
            return f"!!TEXT NOT FOUND: {key}!!"
        except Exception as e:
            return f"!!TEXT ERROR: {e}!!"

# Создаем единый экземпляр, который будет использоваться во всем боте
texts = TextMessages()