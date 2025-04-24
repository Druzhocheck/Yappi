import json

class Translator():
    mission_json = {"mission::Plan": { "name": "Mission", "note": "Описание миссии", "tasks": [] }}

    def __init__(self, commands: dict) -> None:
        tasks = []
        for command in commands:
            for key, value in command.items():
                if (key == "обследование_фигуры") or ((key == "обследование_точки") and (value["траектория"] == "меандр")):
                    device = False
                    tasks.append(self.action(value["прибор"], "вкл"))
                    
                    for _, coordinate in command[key]["координаты"].items():
                        for i in coordinate:
                            tasks.append(self.movement(value["высота"], value["скорость"], i[0], i[1]))
                            
                            if not device:
                                tasks.append(self.action(value["прибор"], "пауза"))
                                device = True
                            else:
                                tasks.append(self.action(value["прибор"], "продолжить"))
                                device = False
                    tasks.append(self.action(value["прибор"], "выкл"))

                elif key == "обследование_точки":
                    tasks.append(self.action(value["прибор"], "вкл"))
                    for _, coordinate in command[key]["координаты"].items():
                        for i in coordinate:
                            tasks.append(self.movement(value["высота"], value["скорость"], i[0], i[1]))

                    tasks.append(self.action(value["прибор"], "выкл"))
        
        self.mission_json["mission::Plan"]["tasks"] = tasks
        self.save_to_file(self.mission_json)

    def get_mission_json(self):
        return self.mission_json
    
    def movement(self, depth, speed, lon, lat) -> dict:
        return {
                "id": "TackPoint",
                "TackPointUp": depth,
                "TackPointVelocity": speed,
                "TackPointLon": lon,
                "TackPointLat": lat,
                # "TackPointPitch": 0, добавить в новой версии
                # "TackPointBreak": 0
        }

    def action(self, device : str, status):
        if device == "гбо":
            if status == "вкл":
                return {
                    "id": "SidesonarOn",
                    "SidesonarDist": 100,
                    "SidesonarPulse": 1500,
                    "SidesonarDecimation": 1,
                    "SidesonarRawData": False
                    }
            
            elif status == "пауза":
                return {
                        "id": "SidesonarPause"
                    }
            elif status == "продолжить":
                return {
                        "id": "SidesonarResume"
                    }
            elif status == "выкл":
                return {
                    "id": "SidesonarOff"
                    }
            
        elif device == "млэ":
            if status == "вкл":
                return {
                        "id": "MBEOnHf"
                    }
            elif status == "пауза":
                return {
                        "id": "MBEPause"
                    }
            elif status == "выкл":
                return {
                        "id": "MBEOff"
                    }
        elif device == "фотокамера":
            return       {
        "id": "PhotoOn",
        "PhotoPeriod": 2,
        "PhotoLight": 100,
        "PhotoExposure": 7000,
        "PhotoGain": 1,
        "PhotoAuto": "true"
      }
    
    def save_to_file(self, data) -> None:
        """Сохраняет данные в JSON файл."""
        with open("mission.json", 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)