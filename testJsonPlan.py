from Process.jsonPlan import *

# load OpenTPS plan
file_path = '../data/liver/patient_0/MidP_CT/OpenTPS/ITV_based/treatment_plan_optimized.tps'
plan = RTplan()
plan.load(file_path)

# Config
config_file = 'config.txt'

# Create BDT object
BDT = BDT(plan, config_file)
# get timings
plan_with_timings = BDT.get_PBS_timings(sort_spots="true")

# Save plan with timings
# plan_with_timings.save('../data/liver/patient_0/MidP_CT/OpenTPS/ITV_based/treatment_plan_optimized_with_timings.tps')

print('Spot timings')
print(plan_with_timings.Beams[0].Layers[1].SpotTiming)
print('Position x')
print(plan_with_timings.Beams[0].Layers[1].ScanSpotPositionMap_x)
print('Position y')
print(plan_with_timings.Beams[0].Layers[1].ScanSpotPositionMap_y)
print('Spot MU')
print(plan_with_timings.Beams[0].Layers[1].SpotMU)
print('Sum MU')
print(np.sum(plan_with_timings.Beams[0].Layers[1].SpotMU))