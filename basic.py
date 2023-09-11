

class John:
    
    def __init__(self):
        self.y = 37
    
    def print_world(self):
        print(self.y)
    
    def multiply(self):
        self.y = self.y * 2
    

print('hi')


j = John()
j.y = 5
j.print_world()