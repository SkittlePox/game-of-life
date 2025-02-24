import gym
import numpy as np
from lib import fft_convolve2d


class ConwayEnv(gym.Env):
    metadata = {"render.modes": ['rgb_array']}

    def __init__(self, action_shape=(3, 3), state_shape=(10, 10), goal_location=(6, 6), start_state=None, k=None):
        """
        state_shape dimensions must be even, though not necessarily equal!!
        """

        self.action_shape = action_shape
        self.state_shape = state_shape
        self.action_space = gym.spaces.MultiBinary(action_shape)
        self.observation_space = gym.spaces.MultiBinary(state_shape)

        if start_state is None:
            start_state = np.zeros(state_shape, dtype=np.int8)

        self.start_state = np.copy(start_state)
        self.state = start_state
        self.goal_location = goal_location

        self.action_view = None
        self.goal_view = None
        self.state_reset()
        self.goal_view.fill(1)

        self.num_action_pixels = 0
        self.prior_action = np.zeros(action_shape)

        if k is None:
            m, n = state_shape
            k = np.zeros((m, n))
            k[m // 2 - 1: m // 2 + 2, n // 2 - 1: n // 2 + 2] = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        self.k = k

    def step(self, action):
        # apply actions
        self.prior_action = action
        np.logical_xor(action, self.action_view, out=self.action_view, dtype=np.int8, casting='unsafe')

        b = fft_convolve2d(self.state, self.k).round()

        c = np.zeros(b.shape)
        c[np.where((b == 2) & (self.state == 1))] = 1
        c[np.where((b == 3) & (self.state == 1))] = 1
        c[np.where((b == 3) & (self.state == 0))] = 1

        # This fixes environment wrap-around
        c[:, [0, -1]] = c[[0, -1]] = 0

        self.state = c.astype(np.int8)
        self.state_reset()

        done = not not np.all(np.logical_not(self.goal_view).astype(np.int8))

        # This reward function encourages keeping at least one square 'on' which prevents termination
        # reward = float(np.sum(np.logical_not(self.goal_view).astype(np.int8)))

        # This is a super simple reward function
        reward = 10.0 if done else -0.1

        # This reward function adds an additional cost to taking some actions
        # self.num_action_pixels += np.sum(action)
        # penal = np.power(2, self.num_action_pixels*0.01) * np.sum(action) * 0.01
        # penal = min(penal, 100)
        # reward -= penal

        return self.state, reward, done, {}

    def state_reset(self):
        self.action_view = self.state[2:2 + self.action_shape[0], 2:2 + self.action_shape[1]]
        self.goal_view = self.state[self.goal_location[0]:self.goal_location[0] + 2,
                         self.goal_location[1]:self.goal_location[1] + 2]

    def reset(self):
        self.state = np.zeros(self.state_shape, dtype=np.int8)
        # self.state = np.copy(self.start_state)
        self.state_reset()
        self.goal_view.fill(1)
        self.num_action_pixels = 0
        return self.state

    def render(self, mode='rgb_array'):
        if mode == 'rgb_array':
            kron_size = 20
            s = np.copy(self.state)
            # s = np.pad(s, pad_width=1)
            s = np.kron(s, np.ones((kron_size, kron_size)))
            s = np.dstack((s, s, s)).astype(dtype=np.uint8) * 255

            # separate action layer

            # render_action_view = s[2 * kron_size:2 * kron_size + self.action_shape[0] * kron_size,
            #                      2 * kron_size:2 * kron_size + self.action_shape[1] * kron_size]
            # render_action = np.kron(self.prior_action, np.ones((kron_size, kron_size)))

            return s


class FlatObservationWrapper(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        self.original_shape = self.observation_space.n
        self.observation_space = gym.spaces.MultiBinary(n=np.product(self.observation_space.n))

    def observation(self, obs):
        observation = obs.reshape(np.product(self.observation_space.n))
        return observation


class FlatActionWrapper(gym.ActionWrapper):
    def __init__(self, env):
        super().__init__(env)
        self.original_shape = self.action_space.n
        self.action_space = gym.spaces.MultiBinary(n=np.product(self.action_space.n))

    def action(self, act):
        action = act.reshape(self.original_shape)
        return action
