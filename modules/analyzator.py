import re
from typing import Any, Dict, List, Optional

    
# данный файл определяет конструкции языка - переменная, функция, условие
# класс для определение типа конструкции
class Lexical:

    def __init__(self, token :str):
        self.token = token

    #* проверка является токен переменной
    def isvariable(self) -> bool:
        if "=" in self.token:
            return True
        else:
            return False
        
    #* проверка является токен функцией
    def isfunction(self) -> bool:
        if "(" in self.token and (
                        self.token.count("(") > self.token.count(")") or 
                        (self.token.count("(") == self.token.count(")") and 
                        self.token[self.token.rfind(")")-1] == ")")
                        ):
            return True
        else:
            return False
        
    #* проверка является токен началом условия
    def iscondition(self) -> str:
        if self.token.strip().startswith('событие'):
            return True
        else:
            return False
    
    #* опредление типа переменной
    def check_type(self) -> str:
        if self.isvariable():
            return "variable"
        elif self.isfunction():
            return "function"
        elif self.iscondition():
            return "condition"
    #* в случае, если не подходит ни под какое условие, будем считать, что это продолжение предыдущей строки
        else:
            return "addition"
    
    def get_type(self) -> str:
        return self.check_type()

class Variables:
    """
    Класс для хранения и управления переменными миссии.
    Реализует безопасное хранение, установку и получение переменных.
    """
    
    __slots__ = ('_variables',)
    
    def __init__(self) -> None:
        self._variables: Dict[str, Any] = {}
    
    @property
    def variables(self) -> Dict[str, Any]:
        """Возвращает словарь всех переменных (только для чтения)."""
        return self._variables.copy()
    
    def set_raw_variable(self, raw_variable: str) -> None:
        """
        Устанавливает значение переменной из сырой строки формата 'name=value'.
        
        Args:
            raw_variable: Строка с определением переменной.
        """
        name, value = map(str.strip, raw_variable.split('=', 1))
        self._variables[name] = value
    
    def set_variable(self, name: str, value: str) -> None:
        """
        Устанавливает значение переменной с попыткой вычисления выражения.
        
        Args:
            name: Имя переменной.
            value: Значение или выражение для вычисления.
        """
        try:
            self._variables[name] = eval(value)
        except (NameError, SyntaxError):
            self._variables[name] = value
    
    def get_variable_names(self) -> List[str]:
        """Возвращает список имен всех переменных."""
        return list(self._variables.keys())
    
    def get_variable(self, name: str, default: Optional[Any] = None) -> Any:
        """
        Возвращает значение переменной с попыткой его вычисления.
        
        Args:
            name: Имя переменной.
            default: Значение по умолчанию, если переменная не существует.
            
        Returns:
            Значение переменной или default, если переменная не существует.
        """
        if name not in self._variables:
            return default
            
        value = self._variables[name]
        try:
            return eval(value) if isinstance(value, str) else value
        except (NameError, SyntaxError):
            return value
    
    def __contains__(self, name: str) -> bool:
        """Проверяет, существует ли переменная с указанным именем."""
        return name in self._variables
    
    def __getitem__(self, name: str) -> Any:
        """Возвращает значение переменной через синтаксис квадратных скобок."""
        return self.get_variable(name)
    
    def __setitem__(self, name: str, value: Any) -> None:
        """Устанавливает значение переменной через синтаксис квадратных скобок."""
        self._variables[name] = value

# класс для обработки функций разрабатываемого языка
class Commands():

    def __init__(self) -> None:
        pass

    #* метод для задания команды
    def set_raw_command(self, raw_command :str) -> list:
        #* Регулярное выражение для извлечения ключ=значение
        pattern = re.compile(r'(\w+)\(([^)]+)\)')
        # Поиск всех пар ключ-значение и создание словаря с преобразованием значений к числу с плавающей точкой, если это возможно
        result = {key: (float(value) if value.replace('.', '', 1).isdigit() else value) for key, value in pattern.findall(raw_command.strip(raw_command.split('(')[0].strip()))}
        self.command = {self.set_title_command(raw_command) : result}
        return self.command
    
    #* определяем название команды
    def set_title_command(self, raw_command :str) -> None:
        return raw_command.split('(')[0].strip()

    #* метод класса для задания параметров словарю
    #! не нужный метод класса
    def set_command(self, key :str, value) -> dict:
        self.command[key] = value
        return self.command
    
    #* возвращаем массив функций
    def get_command(self) -> dict:
        return self.command
    
class Conditions():
    pass

class Analyzator:
    """Класс для выполнения лексического, синтаксического и семантического анализа."""

    def __init__(self, data: list):
        """
        Инициализация анализатора.
        
        :param data: Список строк для анализа.
        """
        self.data = data
        self.variables = Variables()  # Хранение переменных
        self.commands = Commands()  # Хранение команд
        self.conditions = Conditions()  # Хранение условий

    def lexical_analysis(self) -> tuple[list[str], list[str]]:
        """
        Лексический анализ входных данных.
        
        :return: Кортеж из списков типов токенов и самих токенов.
        """
        tokens = []
        token_types = []

        for line in self.data:
            lex = Lexical(line)
            token_type = lex.get_type()

            if token_type == "addition" and tokens:
                tokens[-1] += f" {line}"  # Объединяем добавления с предыдущей строкой
            else:
                tokens.append(line)
                token_types.append(token_type)

        return token_types, tokens

    def syntactic_analysis(self, token_type: str, token: str) -> dict:
        """
        Синтаксический анализ токена.
        
        :param token_type: Тип токена (например, "function", "condition").
        :param token: Сам токен.
        :return: Результат анализа (например, команда или условие).
        """
        if token_type == "function":
            raw_command = self.commands.set_raw_command(token)
            return self.semantic_analysis(raw_command)
        elif token_type == "condition":
            # Обработка условий (можно расширить в будущем)
            return {"type": "condition", "value": token}
        return {}

    def semantic_analysis(self, command: dict) -> dict:
        """
        Семантический анализ команды.
        
        :param command: Команда для анализа.
        :return: Команда с подставленными значениями переменных.
        """
        for key, value in command.items():
            for param, param_value in value.items():
                if param_value in self.variables.get_variable_names():
                    command[key][param] = self.variables.get_variable(param_value)
        return command

    def analyze(self) -> list:
        """
        Главный метод для выполнения полного анализа.
        
        :return: Список обработанных токенов.
        """
        token_types, tokens = self.lexical_analysis()
        result = []

        for token_type, token in zip(token_types, tokens):
            if token_type == "variable":
                self.variables.set_raw_variable(token)
            else:
                result.append(self.syntactic_analysis(token_type, token))

        return result