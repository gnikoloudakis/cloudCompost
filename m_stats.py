class Stats(object):
    points = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ]
    average = 0.0
    count = 0

    @staticmethod
    def add_points(val):
        Stats.count += 1
        if Stats.count > 10:
            Stats.points.pop(0)
            Stats.points.append(val)
            return sum(Stats.points)/10
