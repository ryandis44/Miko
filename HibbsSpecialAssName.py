class RocketLeagueCar:
    
    def __init__(self, body_type: str, color: str, wheel_type: str, boost: str, goal_explosion: str, name: str, save_slot: int):
        self.body_type = body_type
        self.color = color
        self.wheel_type = wheel_type
        self.boost = boost
        self.goal_explosion = goal_explosion
        self.name = name
        self.save_slot = save_slot
        
    def print_car_name(self):
        print(self.name)
    
    def car_slot_times_two(self):
        return self.save_slot * 2
    

fennec = RocketLeagueCar(
    body_type="Fennec",
    color="Blue",
    wheel_type="Christiano",
    boost="Gold Rush (Alpha Reward)",
    goal_explosion="Phoenix Cannon",
    name="shitty car",
    save_slot=1
)

fennec.color = "Red"
print(fennec.color)