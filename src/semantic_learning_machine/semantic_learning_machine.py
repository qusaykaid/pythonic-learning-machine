from neural_network.node import Sensor, create_neuron
from numpy import array, matrix, dot
from numpy.linalg import pinv
from data.data_set import get_input_variables, get_target_variable
from neural_network.neural_network import NeuralNetwork
from neural_network.connection import Connection
from random import choice, uniform, sample, randint
from semantic_learning_machine.solution import Solution, create_solution
from copy import copy
from utils.calculations import root_mean_squared_error


class SemanticLearningMachine(object):
    """"""
    def __init__(self, stopping_criterion, population_size, layers,
                 learning_step, max_connections, mutation_operator,
                 training_set, validation_set, testing_set, is_classification):
        self.stopping_criterion = stopping_criterion
        self.population_size = population_size
        self.layers = layers
        self.learning_step = learning_step
        self.max_connections = max_connections
        self.mutation_operator = mutation_operator
        self.training_set = training_set
        self.validation_set = validation_set
        self.testing_set = testing_set
        self.is_classification = is_classification
        self.population = None
        self.current_champion = None
        self.next_champion = None
        self.current_generation = 0
        self.log = None

    def _get_learning_step(self, partial_semantics):
        """"""
        if self.learning_step == 'optimized':
            return self._get_optimized_learning_step(partial_semantics)
        else:
            return self.learning_step

    def _get_optimized_learning_step(self, partial_semantics):
        """"""
        delta_target = array(get_target_variable(self.training_set))
        if self.current_champion:
            delta_target -= self.current_champion.neural_network.get_predictions()
        inverse = array(pinv(matrix(partial_semantics)))
        return dot(inverse.transpose(), delta_target)

    def _get_connection_weight(self, weight):
        return weight if weight else uniform(-1, 1)

    def _connect_nodes(self, from_nodes, to_nodes, weight=None, random=False):
        if random:
            max_connections = self.max_connections if len(from_nodes) > self.max_connections else len(from_nodes)
            random_connections = randint(1, max_connections)
            from_nodes_sample = sample(from_nodes, random_connections)
        else:
            from_nodes_sample = from_nodes
        [[Connection(from_node, to_node, self._get_connection_weight(weight))
          for from_node in from_nodes_sample] for to_node in to_nodes]

    def _connect_nodes_mutation(self, hidden_layers):
        """Connects new mutation neurons to remainder of network."""

        # Sets reference to champion neural network.
        neural_network = self.current_champion.neural_network

        # Create hidden origin layer.
        from_layers = [copy(hidden_layer) for hidden_layer in hidden_layers]
        [hidden_layer_new.extend(hidden_layer_old) for hidden_layer_new, hidden_layer_old
         in zip(from_layers, neural_network.hidden_layers)]

        # Establish connections.
        self._connect_nodes(neural_network.sensors, hidden_layers[0])
        previous_neurons = from_layers[0]
        for from_layer, to_layer in zip(from_layers[1:], hidden_layers[1:]):
            self._connect_nodes(previous_neurons, to_layer)
            previous_neurons = from_layer

    def _initialize_hidden_layers(self):
        hidden_layers = [[create_neuron()] for i in range(self.layers - 1)]
        hidden_layers.append([create_neuron('tanh')])
        return hidden_layers

    def initialize_solution(self, sensors):
        # Create output neuron.
        output_neuron = create_neuron('identity')

        # Create hidden layer.
        hidden_layers = self._initialize_hidden_layers()

        # Establish connections
        self._connect_nodes(sensors, hidden_layers[0], random=True)
        previous_neurons = hidden_layers[0]
        for hidden_layer in hidden_layers[1:]:
            self._connect_nodes(previous_neurons, hidden_layer, random=False)
            previous_neurons = hidden_layer

        # Calculate hidden neurons.
        [[neuron.calculate() for neuron in layer] for layer in hidden_layers]

        # Get partial, hidden semantics.
        partial_semantics = hidden_layers[-1][0].semantics

        # Connect last hidden neuron to output neuron.
        self._connect_nodes(previous_neurons, [output_neuron], self._get_learning_step(partial_semantics), random=False)

        # Create neural network.
        neural_network = NeuralNetwork(sensors, hidden_layers, output_neuron)

        # Calculate output semantics.
        neural_network.output_neuron.calculate()

        # Create solution.
        solution = create_solution(None, neural_network, get_target_variable(self.training_set))

        # Return solution.
        return solution

    def create_initial_population(self):
        # Create sensors
        sensors = [Sensor(array(self.training_set[input_variable])) for input_variable in get_input_variables(self.training_set)]

        # Initialize random champion
        self.current_champion = self.initialize_solution(sensors)

    def mutate_champion(self):
        # Creates shallow copy of champion.
        offspring = copy(self.current_champion)

        # Create hidden layers.
        hidden_layers = self.mutation_operator.mutate_network(self.current_champion.neural_network)

        # Extend hidden layers.
        [hidden_layer.extend(mutation_layer) for hidden_layer, mutation_layer
         in zip(offspring.neural_network.hidden_layers, hidden_layers)]


        # Connect hidden neurons to remainder of network.
        self._connect_nodes_mutation(hidden_layers)

        # Calculate hidden layer.
        for hidden_layer in hidden_layers:
            [neuron.calculate() for neuron in hidden_layer]

        # All neurons are calculated, for now we assume a fixed learning step approach.
        # TODO: Implement Optimized Learning Step

        # new_semantics = hidden_neurons[-1].semantics * self._get_learning_step()
        # new_error = offspring.error + new_semantics
        # new_mean_error = root_mean_squared_error(new_error)

        # TODO: If new_mean_error is less than mean_error of old_champion and next_champion, then create new neural network.
