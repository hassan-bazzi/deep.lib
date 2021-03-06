import torch
import torch.nn as nn
import torch.optim as optim
from LR_Schedule.lr_scheduler import _LRScheduler, _OnBatchLRScheduler
import matplotlib.pyplot as plt
from session import Session, TrainingSchedule
import math
import util

class LRFindScheduler(_OnBatchLRScheduler):
    def __init__(self, num_examples, start_lr=None, end_lr=10):
        super(LRFindScheduler, self).__init__()       
        self.losses = []
        self.end_lr = end_lr
        self.num_examples = num_examples
        self.start_lr = start_lr

    def on_train_begin(self, session):
        super(LRFindScheduler, self).on_train_begin(session)
        if self.start_lr is not None: self.base_lrs = util.listify(self.start_lr, session.optimizer.param_groups)
        self.multipliers = [(self.end_lr/base_lr)**(1/self.num_examples) for base_lr in self.base_lrs]
        self.lrs = []
        self.best=1e9
    
    def get_lr(self):
        new_lr = [base_lr * mult ** self.iteration for base_lr, mult in zip(self.base_lrs, self.multipliers)]
        self.lrs.append(new_lr)
        return new_lr

    def on_batch_end(self, session, lossMeter):
        self.losses.append(lossMeter.debias)
        if (math.isnan(lossMeter.debias) or lossMeter.debias > self.best*4):
            session.stop()
        if (lossMeter.debias<self.best and self.iteration>10): self.best=lossMeter.debias

    def plot(self, iterations=None):
        if(iterations is None): iterations = self.iteration

        fig, ax_loss = plt.subplots()   
        ax_lr = ax_loss.twinx()

        ax_loss.set_xlabel("Iteration")
        ax_loss.set_ylabel("Loss", color='g')

        ax_lr.set_yscale("log")
        ax_lr.set_ylabel("Learning Rate (Log Scale)", color='b')

        ax_loss.plot(range(iterations), self.losses, 'g-')
    
        for lr in [*zip(*self.lrs)]: # Matrix transposition
            ax_lr.plot(range(iterations), lr, 'b-')


def lr_find(session, data, start_lr=None, end_lr=10):
    session.save('temp')
    lr_scheduler = LRFindScheduler(len(data), start_lr, end_lr)
    schedule = TrainingSchedule(data, [lr_scheduler])
    session.train(schedule, 1)
    lr_scheduler.plot()
    session.load('temp')
