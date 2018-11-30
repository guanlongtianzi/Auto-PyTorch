__author__ = "Max Dippel, Michael Burkart and Matthias Urban"
__version__ = "0.0.1"
__license__ = "BSD"


from autonet.pipeline.base.pipeline_node import PipelineNode
from autonet.components.preprocessing.preprocessor_base import PreprocessorBase

import ConfigSpace
import ConfigSpace.hyperparameters as CSH
from autonet.utils.configspace_wrapper import ConfigWrapper
from autonet.utils.config.config_option import ConfigOption
from autonet.components.preprocessing.preprocessor_base import PreprocessorBase

class PreprocessorSelector(PipelineNode):
    def __init__(self):
        super(PreprocessorSelector, self).__init__()
        self.preprocessors = dict()
        self.add_preprocessor('none', PreprocessorBase)

    def fit(self, hyperparameter_config, pipeline_config, X_train, Y_train, X_valid, one_hot_encoder):
        hyperparameter_config = ConfigWrapper(self.get_name(), hyperparameter_config)

        preprocessor_name = hyperparameter_config['preprocessor']
        preprocessor_type = self.preprocessors[preprocessor_name]
        preprocessor_config = ConfigWrapper(preprocessor_name, hyperparameter_config)
        preprocessor = preprocessor_type(preprocessor_config)
        preprocessor.fit(X_train, Y_train)

        if preprocessor_name != 'none':
            one_hot_encoder = None

        X_train = preprocessor.transform(X_train)
        if (X_valid is not None):
            X_valid = preprocessor.transform(X_valid)

        return {'X_train': X_train, 'X_valid': X_valid, 'preprocessor': preprocessor, 'one_hot_encoder': one_hot_encoder}

    def predict(self, preprocessor, X):
        return { 'X': preprocessor.transform(X) }

    def add_preprocessor(self, name, preprocessor_type):
        if (not issubclass(preprocessor_type, PreprocessorBase)):
            raise ValueError("preprocessor type has to inherit from PreprocessorBase")
        if (not hasattr(preprocessor_type, "get_hyperparameter_search_space")):
            raise ValueError("preprocessor type has to implement the function get_hyperparameter_search_space")
            
        self.preprocessors[name] = preprocessor_type

    def remove_preprocessor(self, name):
        del self.preprocessors[name]

    def get_hyperparameter_search_space(self, **pipeline_config):
        pipeline_config = self.pipeline.get_pipeline_config(**pipeline_config)
        cs = ConfigSpace.ConfigurationSpace()

        possible_preprocessors = set(pipeline_config["preprocessors"]).intersection(self.preprocessors.keys())
        selector = cs.add_hyperparameter(CSH.CategoricalHyperparameter("preprocessor", possible_preprocessors))
        
        for preprocessor_name, preprocessor_type in self.preprocessors.items():
            if (preprocessor_name not in possible_preprocessors):
                continue
            preprocessor_cs = preprocessor_type.get_hyperparameter_search_space()
            cs.add_configuration_space( prefix=preprocessor_name, configuration_space=preprocessor_cs, delimiter=ConfigWrapper.delimiter, 
                                        parent_hyperparameter={'parent': selector, 'value': preprocessor_name})

        return self._apply_user_updates(cs)

    def get_pipeline_config_options(self):
        options = [
            ConfigOption(name="preprocessors", default=list(self.preprocessors.keys()), type=str, list=True, choices=list(self.preprocessors.keys())),
        ]
        return options