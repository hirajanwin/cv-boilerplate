from enum import Enum
from omegaconf import DictConfig
from ignite.contrib.handlers.tensorboard_logger import *
from ignite.engine import Engine, Events

from utils.visdom_utils import Visualizer, VisPlot, VisImg
from utils.log_operations import LOG_OP

from typing import Callable, List, Dict, Any, Union, Tuple

# Defining a custom type for clarity
LOG_OP_ARGS = Union[List[str], List[VisPlot], List[VisImg]]


class LogTimeLabel(Enum):
    
    @classmethod
    def global_iteration(engine: Engine):
        return engine.state.epoch_length * engine.state.epoch + engine.state.iteration

    CUR_ITER_IN_EPOCH = lambda engine: (
        global_iteration(engine)
        "Epoch[{:d}], Iter[{:d}]".format(engine.state.epoch, engine.state.iteration),
    )
    GLOBAL_ITER = lambda engine: (
        global_iteration(engine)
        "Global Iter[{:d}]".format(
            engine.state.epoch_length * engine.state.epoch + engine.state.iteration
        ),
    )
    CUR_EPOCH = lambda engine: (
        engine.state.epoch,
        "Epoch[{:d}]".format(engine.state.epoch),
    )


class EngineStateAttr(Enum):
    METRICS = "metrics"  # engine.state.metrics
    OUTPUT = "output"  # engine.state.output


class LogDirector:
    def __init__(self, cfg: DictConfig, engines: List[Engine] = None):
        # TODO: Set up a Tensorboard contrib.handler
        self.tb_writer = None

        self.registered_engines = {}

        # Spin up Visdom server
        self.vis = Visualizer(cfg)

        if engines:
            self.register_engines(engines)

    def startup_engine(self, engine: Engine) -> None:
        engine.state.fp = {}
        engine.state.vis = self.vis

    def register_engines(self, engines: List[Engine]) -> None:
        for eng in engines:
            eng.add_event_handler(Events.STARTED, self.startup_engine)
            self.registered_engines[eng.logger.name] = eng

    def print_event_handlers(self):
        # TODO: Should pretty print all the event handlers
        raise NotImplementedError()

    # Set's up a bunch of log handlers
    def set_event_handlers(
        self,
        engine: Engine,
        event: Events,
        engine_attr: EngineStateAttr,
        log_operations: List[Tuple[LOG_OP, LOG_OP_ARGS]],
        log_time_label: LogTimeLabel = LogTimeLabel.CUR_ITER_IN_EPOCH,
        pre_op: Callable[[Any], Engine] = None,
    ):

        log_op_callables = lambda engine: [
            (
                log_op(
                    pre_op() if pre_op else engine,
                    self.vis,
                    op_args,
                    engine_attr=engine_attr.value,
                    time_label=log_time_label(engine)[0],
                )
            )
            if log_op is LOG_OP.NUMBER_TO_VISDOM or log_op is LOG_OP.IMAGE_TO_VISDOM
            else log_op(
                pre_op() if pre_op else engine,
                op_args,
                engine_attr=engine_attr.value,
                time_label=log_time_label(engine)[1],
            )
            for log_op, op_args in log_operations
        ]

        # Bind the callables list to the event handler
        engine.add_event_handler(event, log_op_callables)

        lambda engine: preop() if pre_op else engine
