from __future__ import annotations
from typing import List, Iterable
import sys
from pathlib import Path

class Parser:
    """
    Класс для чтения и предварительной обработки файлов миссий.
    Реализует чтение файла, удаление комментариев и пустых строк.
    """
    
    __slots__ = ('_filename', '_machine')
    
    def __init__(self, filename: str, machine: str) -> None:
        """
        Инициализация парсера.
        
        Args:
            filename: Путь к файлу миссии
            machine: Целевой аппарат
        """
        self._filename = Path(filename)
        self._machine = machine
    
    @property
    def filename(self) -> Path:
        """Возвращает путь к файлу как объект Path."""
        return self._filename
    
    @property
    def machine(self) -> str:
        """Возвращает название целевого аппарата."""
        return self._machine
    
    def read_lines(self) -> List[str]:
        """
        Читает файл и возвращает список строк.
        
        Returns:
            Список строк файла
            
        Raises:
            SystemExit: Если файл не может быть прочитан
        """
        try:
            with self._filename.open(encoding='utf-8') as f:
                return f.readlines()
        except (IOError, OSError) as e:
            print(f"Ошибка при открытии файла: {e}", file=sys.stderr)
            sys.exit(1)
    
    @staticmethod
    def preprocess_lines(lines: Iterable[str]) -> List[str]:
        """
        Обрабатывает строки: удаляет комментарии, пустые строки, лишние пробелы.
        
        Args:
            lines: Итерируемый объект со строками
            
        Returns:
            Обработанный список строк
        """
        return [
            line.strip() 
            for line in lines 
            if line.strip() and not line.lstrip().startswith('#')
        ]
    
    def get_tokens(self) -> List[str]:
        """
        Основной метод получения обработанных токенов.
        
        Returns:
            Обработанный список строк (токенов)
        """
        raw_lines = self.read_lines()
        return self.preprocess_lines(raw_lines)
    
    def __call__(self) -> List[str]:
        """Альтернативный интерфейс для получения токенов."""
        return self.get_tokens()