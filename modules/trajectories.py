import math
import re
from typing import Dict, List, Any, Tuple, Union

class GeoCoordinateConverter:
    """Конвертер географических координат между форматами."""
    
    DIRECTION_MAP = {
        'СШ': 1, 'N': 1, 'ЮШ': -1, 'S': -1,
        'ВД': 1, 'E': 1, 'ЗД': -1, 'W': -1
    }
    DEGREE_SYMBOLS = {'°', '*', "'", '"', '′', '″'}
    DMS_PATTERN = re.compile(r'(\d+\.?\d*)[*°]?[\s]*(\d+\.?\d*)?[\'′]?[\s]*(\d+\.?\d*)?["″]?')

    @classmethod
    def dms_to_decimal(cls, dms_str: str) -> float:
        """Конвертирует координаты из DMS в десятичные градусы."""
        sign = 1
        cleaned_str = dms_str.upper()
        for marker, value in cls.DIRECTION_MAP.items():
            if marker in cleaned_str:
                sign *= value
                cleaned_str = cleaned_str.replace(marker, '')
                break

        match = cls.DMS_PATTERN.match(cleaned_str.strip())
        if not match:
            raise ValueError(f"Invalid coordinate format: {dms_str}")

        degrees = float(match[1])
        minutes = float(match[2] or 0)
        seconds = float(match[3] or 0)

        return sign * (degrees + minutes/60 + seconds/3600)

    @classmethod
    def parse_coordinate(cls, coord_str: str) -> float:
        """Парсит координату в различных форматах."""
        if not any(c in coord_str for c in cls.DEGREE_SYMBOLS):
            raise ValueError("Invalid coordinate format - missing degree symbol")

        if not any(c in coord_str for c in ["'", '"', '′', '″']):
            parts = re.split(r'[*°]', coord_str, 1)
            value = float(parts[0])
            direction = parts[1].strip()
            return value * (-1 if direction in {'ЗД', 'ЮШ', 'W', 'S'} else 1)
        
        return cls.dms_to_decimal(coord_str)

    @classmethod
    def convert_coordinates(cls, lon_str: str, lat_str: str) -> Tuple[float, float]:
        """Конвертирует пару координат в десятичные градусы."""
        return cls.parse_coordinate(lon_str), cls.parse_coordinate(lat_str)

class TrajectoryGenerator:
    """Базовый класс для генерации траекторий."""
    
    EARTH_RADIUS = 6_371_000
    DEG_TO_RAD = math.pi / 180
    RAD_TO_DEG = 180 / math.pi
    COS_LAT_THRESHOLD = 1e-12
    METERS_PER_DEGREE = 111320

    @classmethod
    def add_meters_to_coordinates(
        cls,
        lat: float,
        lon: float,
        meters_north: float,
        meters_east: float
    ) -> Tuple[float, float]:
        """Добавляет метры к координатам с округлением до 6 знаков."""
        if abs(lat) >= 90:
            delta_lat = meters_north / cls.EARTH_RADIUS * cls.RAD_TO_DEG
            return round(lon, 6), round(lat + delta_lat, 6)
        
        lat_rad = lat * cls.DEG_TO_RAD
        delta_lat = meters_north / cls.EARTH_RADIUS * cls.RAD_TO_DEG
        
        cos_lat = math.cos(lat_rad)
        delta_lon = (meters_east / (cls.EARTH_RADIUS * cos_lat) * cls.RAD_TO_DEG 
                    if abs(cos_lat) > cls.COS_LAT_THRESHOLD else 0)
        
        return round(lon + delta_lon, 6), round(lat + delta_lat, 6)

    @classmethod
    def rotate_point(
        cls,
        origin: Tuple[float, float],
        point: Tuple[float, float],
        angle_deg: float
    ) -> Tuple[float, float]:
        """Поворачивает точку относительно origin."""
        ox, oy = origin
        px, py = point
        
        angle_rad = angle_deg * cls.DEG_TO_RAD
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        dx, dy = px - ox, py - oy
        
        return (
            round(ox + cos_a * dx - sin_a * dy, 6),
            round(oy + sin_a * dx + cos_a * dy, 6)
        )

class BaseMeanderGenerator(TrajectoryGenerator):
    """Базовый класс для генерации меандров."""
    
    @classmethod
    def _generate_meander_segment(
        cls,
        start_lon: float,
        start_lat: float,
        width_m: float,
        length_m: float,
        spacing_m: float,
        direction: str
    ) -> List[Tuple[float, float]]:
        """Генерирует сегменты меандра."""
        points = []
        is_vertical = direction == "вертикально"
        size, steps = (length_m, width_m) if is_vertical else (width_m, length_m)
        num_passes = max(1, int(steps / spacing_m))
        
        for i in range(num_passes + 1):
            offset = i * spacing_m
            if is_vertical:
                current = cls.add_meters_to_coordinates(start_lat, start_lon, 0, offset)
                if i % 2 == 0:
                    end = cls.add_meters_to_coordinates(current[1], current[0], size, 0)
                    points.extend([current, end])
                else:
                    top = cls.add_meters_to_coordinates(start_lat, start_lon, size, offset)
                    points.extend([top, current])
            else:
                current = cls.add_meters_to_coordinates(start_lat, start_lon, offset, 0)
                if i % 2 == 0:
                    end = cls.add_meters_to_coordinates(current[1], current[0], 0, size)
                    points.extend([current, end])
                else:
                    right = cls.add_meters_to_coordinates(start_lat, start_lon, offset, size)
                    points.extend([right, current])
        
        return points

class MeanderGenerator(BaseMeanderGenerator):
    """Генератор меандров от начальной точки."""
    
    @classmethod
    def generate_meander(
        cls,
        start_lon: float,
        start_lat: float,
        width_m: float,
        length_m: float,
        spacing_m: float,
        direction: str = "вертикально",
        angle_deg: float = 0
    ) -> List[Tuple[float, float]]:
        points = cls._generate_meander_segment(
            start_lon, start_lat, width_m, length_m, spacing_m, direction)
        return [cls.rotate_point((start_lon, start_lat), p, angle_deg) for p in points] if angle_deg else points

class CenteredMeanderGenerator(BaseMeanderGenerator):
    """Генератор меандров с центром в указанной точке."""
    
    @classmethod
    def generate_centered_meander(
        cls,
        center_lon: float,
        center_lat: float,
        width_m: float,
        length_m: float,
        spacing_m: float,
        direction: str = "вертикально",
        angle_deg: float = 0
    ) -> List[Tuple[float, float]]:
        """
        Генерирует меандр с центром в указанной точке.
        
        :param center_lon: Долгота центральной точки.
        :param center_lat: Широта центральной точки.
        :param width_m: Ширина меандра (в метрах).
        :param length_m: Длина меандра (в метрах).
        :param spacing_m: Расстояние между линиями меандра (в метрах).
        :param direction: Направление меандра ("vertical" или "horizontal").
        :param angle_deg: Угол поворота меандра (в градусах).
        :return: Список точек траектории меандра без начальной точки.
        """
        # Вычисляем начальную точку как смещение от центра влево и вниз
        half_width_m = width_m / 2
        half_length_m = length_m / 2
        
        # Смещаемся от центра к начальной точке
        start_lon, start_lat = cls.add_meters_to_coordinates(
            center_lat, center_lon, -half_length_m, -half_width_m
        )
        
        # Генерируем меандр от начальной точки
        points = cls._generate_meander_segment(
            start_lon, start_lat, width_m, length_m, spacing_m, direction
        )
        
        # Исключаем начальную точку из результата
        if points:
            points = points[1:]  # Пропускаем первую точку
        
        # Поворачиваем меандр, если задан угол
        if angle_deg:
            return [
                cls.rotate_point((center_lon, center_lat), point, angle_deg)
                for point in points
            ]
        
        return points

class SpiralGenerator(TrajectoryGenerator):
    """Оптимизированный генератор спиральных траекторий."""
    
    ANGLE_STEP = math.pi / 8

    @classmethod
    def generate_spiral(
        cls,
        center_lon: float,
        center_lat: float,
        max_radius_m: float,
        spacing_m: float,
        clockwise: bool = True,
        point_freq: int = 1
    ) -> List[Tuple[float, float]]:
        points = [(center_lon, center_lat)]
        direction = 1 if clockwise else -1
        radius = 0
        
        while radius <= float(max_radius_m):
            radius += spacing_m * cls.ANGLE_STEP / (2 * math.pi)
            angle = direction * 2 * math.pi * radius / spacing_m
            dx, dy = radius * math.cos(angle), radius * math.sin(angle)
            if len(points) % point_freq == 0:
                points.append(cls.add_meters_to_coordinates(center_lat, center_lon, dy, dx))
        
        return points

class StarGenerator:
    """Оптимизированный генератор звездообразных фигур."""
    
    @staticmethod
    def generate_star(
        center_lon: float,
        center_lat: float,
        radius_m: float,
        num_lines: int,
        angle_offset: float = 0.0,
        line_length: float = 7.0
    ) -> List[Tuple[float, float]]:
        if num_lines < 2:
            raise ValueError("Количество лучей должно быть ≥ 2")
            
        points = []
        angle_step = 2 * math.pi / num_lines
        cos_lat = math.cos(center_lat * math.pi / 180)
        
        for i in range(int(num_lines)):
            angle = math.radians(angle_offset) + i * angle_step
            outer = (
                center_lon + (line_length * math.cos(angle)) / (111320 * cos_lat),
                center_lat + (line_length * math.sin(angle)) / 111320
            )
            
            if radius_m > 0:
                inner_angle = angle + angle_step / 2
                inner = (
                    center_lon + (radius_m * math.cos(inner_angle)) / (111320 * cos_lat),
                    center_lat + (radius_m * math.sin(inner_angle)) / 111320
                )
                points.extend([outer, inner])
            else:
                points.append(outer)
                
            points.append((center_lon, center_lat))
        
        return [(round(x, 6), round(y, 6)) for x, y in points]

class RosetteGenerator:
    """Генератор розеточных траекторий."""
    
    @staticmethod
    def generate_rosette(
        center_lon: float,
        center_lat: float,
        radius_m: float,
        num_passes: int,
        angle_offset: float = 0
    ) -> List[Tuple[float, float]]:
        points = []
        angle_step = math.pi / num_passes
        cos_lat = math.cos(math.radians(center_lat))
        
        for i in range(num_passes):
            angle = math.radians(angle_offset) + i * angle_step
            end = (
                center_lon + (radius_m * math.cos(angle)) / (111320 * cos_lat),
                center_lat + (radius_m * math.sin(angle)) / 111320
            )
            points.extend([end, (center_lon, center_lat)])
        
        return [(round(x, 6), round(y, 6)) for x, y in points]

class ParallelLineGenerator:
    """
    Генератор параллельной линии для заданной последовательности географических точек.
    Параметр 'position' определяет сторону смещения:
    - 'left' - слева от исходной линии (против часовой стрелки)
    - 'right' - справа от исходной линии (по часовой стрелке)
    - 'top' - сверху (севернее) исходной линии
    - 'bottom' - снизу (южнее) исходной линии
    """
    
    EARTH_RADIUS = 6_371_000  # Радиус Земли в метрах
    DEG_TO_RAD = math.pi / 180
    RAD_TO_DEG = 180 / math.pi
    METERS_PER_DEGREE = 111320  # Метров в одном градусе широты

    @classmethod
    def generate_parallel_line(
        cls,
        points: List[Tuple[float, float]],
        distance_m: float,
        position: str = 'right'
    ) -> List[Tuple[float, float]]:
        """
        Генерирует параллельную линию на заданном расстоянии от исходной.
        
        :param points: Исходные точки линии (долгота, широта)
        :param distance_m: Расстояние в метрах для смещения
        :param position: Положение параллельной линии ('left', 'right', 'top', 'bottom')
        :return: Список точек параллельной линии
        """
        if len(points) < 2:
            raise ValueError("Для построения линии нужно минимум 2 точки")
        
        parallel_points = []
        
        # Определяем направление смещения
        if position in ['left', 'right']:
            # Для бокового смещения используем перпендикуляр к направлению линии
            for i in range(len(points)):
                if i == 0:
                    # Первая точка - используем направление к следующей точке
                    angle = cls._calculate_bearing(points[i], points[i+1])
                    offset_angle = angle + (90 if position == 'left' else -90)
                elif i == len(points) - 1:
                    # Последняя точка - используем направление от предыдущей точки
                    angle = cls._calculate_bearing(points[i-1], points[i])
                    offset_angle = angle + (90 if position == 'left' else -90)
                else:
                    # Средние точки - среднее направление между сегментами
                    angle1 = cls._calculate_bearing(points[i-1], points[i])
                    angle2 = cls._calculate_bearing(points[i], points[i+1])
                    offset_angle = (angle1 + angle2) / 2 + (90 if position == 'left' else -90)
                
                # Смещаем точку в перпендикулярном направлении
                parallel_points.append(cls._offset_point(points[i], offset_angle, distance_m))
        else:
            # Для вертикального смещения просто добавляем метры к широте
            sign = 1 if position == 'top' else -1
            for lon, lat in points:
                new_lat = lat + (sign * distance_m / cls.METERS_PER_DEGREE)
                parallel_points.append((lon, new_lat))
        
        return parallel_points

    @classmethod
    def _calculate_bearing(
        cls,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        """
        Вычисляет азимут (в градусах) от point1 к point2.
        """
        lon1, lat1 = map(math.radians, point1)
        lon2, lat2 = map(math.radians, point2)
        
        d_lon = lon2 - lon1
        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360

    @classmethod
    def _offset_point(
        cls,
        point: Tuple[float, float],
        bearing_deg: float,
        distance_m: float
    ) -> Tuple[float, float]:
        """
        Смещает точку на заданное расстояние в заданном направлении.
        """
        lon, lat = point
        bearing_rad = math.radians(bearing_deg)
        lat_rad = math.radians(lat)
        
        angular_distance = distance_m / cls.EARTH_RADIUS
        
        new_lat = math.asin(
            math.sin(lat_rad) * math.cos(angular_distance) +
            math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        
        new_lon = lon + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
            math.cos(angular_distance) - math.sin(lat_rad) * math.sin(new_lat)
        ) * cls.RAD_TO_DEG
        
        return (round(new_lon, 6), round(math.degrees(new_lat), 6))

class SnakeLineGenerator:
    pass

class Figure:
    """Оптимизированный класс для построения траекторий."""
    
    TRAJECTORY_MAP = {
        "меандр": MeanderGenerator.generate_meander,
        "центральный_меандр": CenteredMeanderGenerator.generate_centered_meander,
        "спираль": SpiralGenerator.generate_spiral,
        "звезда": StarGenerator.generate_star,
        "розетка": RosetteGenerator.generate_rosette
    }

    def __init__(self, key: str, command: Dict[str, Any], lon: str, lat: str):
        self.lon, self.lat = GeoCoordinateConverter.convert_coordinates(lon, lat)
        self.key = key
        self.command = command

    def coordinates(self) -> List[Tuple[float, float]]:
        if (trajectory_type := self._get_trajectory_type()) not in self.TRAJECTORY_MAP:
            return []
        
        params = self.command[self.key]
        common = {
            "center_lon": self.lon,
            "center_lat": self.lat,
            "radius_m": params.get("радиус", 10),
            "angle_offset": params.get("угол", 0)
        }

        if trajectory_type == "меандр":
            return self.TRAJECTORY_MAP[trajectory_type](
                self.lon, self.lat,
                params["длина"],
                params["ширина"],
                params["межгалс"],
                params["траектория"].split(", ")[1],
                params.get("угол", 0)
            )
        elif trajectory_type == "центральный_меандр":
            return self.TRAJECTORY_MAP[trajectory_type](
                self.lon, self.lat,
                params["длина"],
                params["ширина"],
                params["межгалс"],
                params["траектория"].split(", ")[1],
                params.get("угол", 0)
            )
        elif trajectory_type == "спираль":
            return self.TRAJECTORY_MAP[trajectory_type](
                self.lon, self.lat,
                float(params["радиус"]),
                float(params["межгалс"]),
                params.get("направление", "по часовой").lower() == "против часовой"
            )
        else:  # звезда или розетка
            return self.TRAJECTORY_MAP[trajectory_type](
                **common,
                num_lines=params.get("линии", 5),
                line_length=params.get("длина_луча", 20)
            ) if trajectory_type == "звезда" else self.TRAJECTORY_MAP[trajectory_type](
                **common,
                num_passes=params.get("проходы", 6)
            )

    def _get_trajectory_type(self) -> Union[str, None]:
        if self.key not in self.command:
            return None
        
       
        traj = self.command[self.key].get("траектория", "").split(",")[0].lower()
        print(traj)
        return (
            "центральный_меандр" if "меандр" in traj and self.key == "обследование_точки" else
            "меандр" if "меандр" in traj else
            "спираль" if "спираль" in traj else
            "звезда" if "звезда" in traj else
            "розетка" if "розетка" in traj or "веер" in traj else None
        )