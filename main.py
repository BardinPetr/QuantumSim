from src.sim.Data.HardwareParams import HardwareParams
from src.sim.Devices.OpticFiber import OpticFiber
from src.sim.MainDevices.ClassicChannel import ClassicChannel
from src.sim.MainDevices.EndpointDevice import EndpointDevice
from src.sim.MainDevices.Users.Alice import Alice
from src.sim.MainDevices.Users.Bob import Bob
from src.sim.Math.Statistics import Statistics

hp = HardwareParams(
    polarization=(1, 0),
    # laser_period=5000,
    # mu=0.1,
    # delta_opt=0,
    # prob_opt=0,
    # pdc=10 ** -5,
    # eff=0.1,
    # dt=1000,
    # fiber_length=0
)

cc = ClassicChannel(ClassicChannel.MODE_LOCAL)

stat = Statistics(hp)
stat.subscribe(Statistics.EVENT_RESULT, Statistics.log_statistics)

# quantum scheme
alice = Alice(hp, classic_channel=cc, session_size=5*10**4)
alice.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.alice_update)

of = OpticFiber(length=hp.fiber_length, deltaopt=hp.delta_opt, probopt=hp.prob_opt)
alice.forward_link(of)

bob = Bob(hp, classic_channel=cc)
bob.subscribe(EndpointDevice.EVENT_KEY_FINISHED, stat.bob_update)

of.forward_link(bob)

alice.start()

# sift key
# alice_sifted_key = []
# bob_sifted_key = []
#
# for i in range(len(bob_info)):
#     if bases[0][i] != bases[1][i] or bob_info[i] == 3:
#         continue
#
#     bob_sifted_key.append(bob_info[i])
#     alice_sifted_key.append(alice_bits[i])
#
# # write statistics
# print("Bases, that Bob and Alice chose for measurement")
# print(bases[0])
# print(bases[1])
#
# print()
#
# print("Information, that Bob receive from waves")
# print(bob_info)
#
# print()
#
# print("Bob's sifted key:  ", bob_sifted_key[:25])
# print("Alice's sifted key:", alice_sifted_key[:25])
#
# print()
#
# print("E(μ):", alice_impulse_count)
# print("Q(μ):", len(list(filter(lambda x: x != 3, bob_info))) / alice_impulse_count)
# print("QBER:", np.sum(np.logical_xor(bob_sifted_key, alice_sifted_key)) / len(bob_sifted_key))
