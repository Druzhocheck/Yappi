import json
from pathlib import Path
from typing import Dict, List, Any, Union, Callable


class ParametersValidator:
    """Класс для валидации параметров команд с обработкой высоты/глубины."""
    # Типы параметров по умолчанию
    PARAM_TYPES: Dict[str, Callable] = {
        'ширина': float,
        'длина': float,
        'высота': float,
        'глубина': float,
        'межгалс': float,
        'радиус': float,
        'скорость': float,
        'угол': float,
        'линии': int,
        'максимальное_время': int,
        'время_без_связи': int
    }

    def __init__(self, parameters_file: Union[str, Path]) -> None:
        self.required_keys: Dict[str, List[str]] = {}
        self.optional_keys: Dict[str, Dict[str, Any]] = {}
        self.trajectory_dependent: Dict[str, Dict[str, List[str]]] = {}
        self._load_parameters(parameters_file)

    def _load_parameters(self, file_path: Union[str, Path]) -> None:
        """Загружает параметры из JSON-файла."""
        try:
            with Path(file_path).open(encoding='utf-8') as file:
                parameters = json.load(file)
                self.required_keys = parameters.get("Required", {})
                self.optional_keys = {
                    cmd: params[0] if isinstance(params, list) and params else {}
                    for cmd, params in parameters.get("Optional", {}).items()
                }
                self.trajectory_dependent = parameters.get("TrajectoryDependent", {})
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Файл параметров не найден: {file_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка в формате JSON файла: {file_path}") from e

    def validate(self, commands_data: List[Dict[str, Dict[str, Any]]]) -> List[Dict[str, Dict[str, Any]]]:
        """Валидирует список команд с обработкой высоты/глубины."""
        return [self._validate_command(cmd) for cmd in commands_data]

    def _validate_command(self, command_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Валидирует одну команду с обработкой высоты/глубины."""
        cmd_name, params = next(iter(command_data.items()))
        
        # Специальная обработка для команды обследование_точки
        if cmd_name == "обследование_точки":
            self._process_point_survey(params)
        
        # Проверка и нормализация высоты/глубины
        self._process_height_depth(cmd_name, params)
        self._check_required_parameters(cmd_name, params)
        self._apply_optional_parameters(cmd_name, params)
        
        # Приведение типов всех параметров
        self._convert_parameter_types(params)
        
        return command_data

    def _process_point_survey(self, params: Dict[str, Any]) -> None:
        """Специальная обработка параметров для команды обследование_точки."""
        # Если траектория не указана, запрашиваем её первой
        if "траектория" not in params:
            params["траектория"] = self._prompt_for_parameter("обследование_точки", "траектория")
        
        # Проверяем зависимые параметры для выбранной траектории
        if "обследование_точки" in self.trajectory_dependent:
            trajectory = params["траектория"].lower()
            for traj, dependent_params in self.trajectory_dependent["обследование_точки"].items():
                if traj in trajectory:  # Проверяем частичное совпадение
                    for param in dependent_params:
                        if param not in params:
                            params[param] = self._prompt_for_parameter("обследование_точки", param)

    def _process_height_depth(self, cmd_name: str, params: Dict[str, Any]) -> None:
        """
        Обрабатывает параметры высоты и глубины:
        - Если указаны оба, оставляет первый параметр.
        - Если указана только глубина, преобразует её в отрицательную высоту.
        - Запрашивает высоту только если она обязательна для данной команды.
        """
        has_height = 'высота' in params
        has_depth = 'глубина' in params

        if has_height and has_depth:
            # Если указаны оба, оставляем высоту и удаляем глубину
            params.pop('глубина')
        elif has_depth:
            # Если указана только глубина, преобразуем в отрицательную высоту
            params['высота'] = -abs(float(params['глубина']))
            params.pop('глубина')
        elif not has_height:
            # Запрашиваем высоту только если она обязательна для данной команды
            if cmd_name in self.required_keys and "высота" in self.required_keys[cmd_name]:
                params['высота'] = self._prompt_for_parameter(cmd_name, "высота")

    def _check_required_parameters(self, cmd_name: str, params: Dict[str, Any]) -> None:
        """Проверяет обязательные параметры."""
        if cmd_name not in self.required_keys:
            return
        for param in self.required_keys[cmd_name]:
            if param not in params:
                params[param] = self._prompt_for_parameter(cmd_name, param)

    def _apply_optional_parameters(self, cmd_name: str, params: Dict[str, Any]) -> None:
        """Добавляет опциональные параметры."""
        if cmd_name not in self.optional_keys:
            return
        for param, default_value in self.optional_keys[cmd_name].items():
            if param not in params:
                params[param] = default_value

    def _convert_parameter_types(self, params: Dict[str, Any]) -> None:
        """Приводит типы параметров к соответствующим типам."""
        for param_name, value in params.items():
            if param_name in self.PARAM_TYPES:
                try:
                    # Пропускаем None значения
                    if value is None:
                        continue
                        
                    # Если значение уже правильного типа, пропускаем
                    if isinstance(value, self.PARAM_TYPES[param_name]):
                        continue
                        
                    # Преобразуем значение
                    params[param_name] = self.PARAM_TYPES[param_name](value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Невозможно преобразовать параметр '{param_name}' "
                        f"со значением '{value}' к типу {self.PARAM_TYPES[param_name].__name__}"
                    )

    def _prompt_for_parameter(self, cmd_name: str, param_name: str) -> Any:
        """Запрашивает значение параметра у пользователя с приведением типа."""
        prompt = f"Введите значение параметра '{param_name}'"
        prompt += f" для команды '{cmd_name}': " if cmd_name else ": "
        
        while True:
            try:
                value = input(prompt)
                
                # Если параметр имеет определенный тип, преобразуем его
                if param_name in self.PARAM_TYPES:
                    return self.PARAM_TYPES[param_name](value)
                return value
            except ValueError:
                print(f"Ошибка: введите корректное значение для параметра {param_name} "
                      f"(ожидается {self.PARAM_TYPES.get(param_name, 'строка')})")

    def save_to_file(self, data: Any, file_path: Union[str, Path]) -> None:
        """Сохраняет данные в JSON файл."""
        with Path(file_path).open('w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def save_to_txt(self, data: List[Dict[str, Dict[str, Any]]], file_path: Union[str, Path]) -> None:
        """Сохраняет данные в текстовый файл."""
        with Path(file_path).open('w', encoding='utf-8') as file:
            for command in data:
                for cmd_name, params in command.items():
                    if cmd_name == "миссия":
                        file.write(f"{cmd_name}(")
                        param_pairs = [f"{k}({v})" for k, v in params.items()]
                        file.write(", ".join(param_pairs).replace("})", ")") + ")\n\n")
                    else:
                        file.write(f"{cmd_name}(\n")
                        for param, value in params.items():
                            file.write(f"    {param}({value}),\n")
                        file.write(")\n\n")