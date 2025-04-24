from modules.parser import Parser
from modules.analyzator import Analyzator
from modules.processing import ParametersValidator
from modules.trajectories import Figure
import json
from modules.translators import Translator

GREEN = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

if __name__ == "__main__":
    app = Parser("mission1.yappi", "mmt-3500") 
    tokens = app.get_tokens()

    analyze = Analyzator(tokens).analyze()
    try:
        validator = ParametersValidator("metadata/parameters.json")
        result = validator.validate(analyze)
        print(f"\n{GREEN}Валидация успешна завершилась.{RESET}\n")
        #validator.save_to_file(result, "verification.yappi.json")
        validator.save_to_txt(result, "verification.yappi")
        print(f"{GREEN}Верифицированный код на ЯППИ записан в файл verification.yappi.{RESET}\n")
    except FileNotFoundError as e:
        print(f"{RED}Ошибка: {e}. Проверьте путь к файлу параметров.{RESET}\n")
    except json.JSONDecodeError:
        print(f"{RED}Ошибка: Некорректный формат JSON в файле параметров.{RESET}\n")
    except Exception as e:
        print(f"{RED}Неизвестная ошибка: {e}{RESET}\n")

    for command in result:
        for key, value in command.items():
            if key in ["обследование_фигуры", "обследование_точки", "обследование_линии"]:
                if 'координаты' in value:
                    # Разделяем координаты на долготу и широту
                    longitude, latitude = map(str, value['координаты'].split(', '))
                    
                    value['координаты'] = {
                        "координаты" : Figure(key, command, longitude, latitude).coordinates()
                        }
    print(result)
    Translator(result)