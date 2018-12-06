from __future__ import print_function, division
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import os
import torch
from skimage import io, transform
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, utils
from complete_dataset import training_toolset
import argparse

import torch
import torchvision
import torchvision.transforms as transforms

import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as init

import torch.optim as optim
import math

from torchvision import datasets, models, transforms
from matplotlib import pyplot as plt
import os, time

from torchsummary import summary
import torch.utils.model_zoo as model_zoo


#torch.set_default_tensor_type('torch.DoubleTensor')

def arg():
	parser = argparse.ArgumentParser(description='save data directory')

	parser.add_argument('--csv_file', dest = 'csv_file', type=str,
					default="/Users/evnw/Research/DeepFasion/attri_predict/landmarks_csv/landmarks.csv")

	parser.add_argument('--img_dir', dest = 'img_folder', type=str,
					default="/Users/evnw/Research/DeepFasion/attri_predict")

	args = parser.parse_args()
	return args

__all__ = ['ResNet', 'resnet18', 'resnet34', 'resnet50', 'resnet101',
		   'resnet152']


model_urls = {
	'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
	'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
	'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
	'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
	'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
}


def conv3x3(in_planes, out_planes, stride=1):
	"""3x3 convolution with padding"""
	return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
					 padding=1, bias=False)


def conv1x1(in_planes, out_planes, stride=1):
	"""1x1 convolution"""
	return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class BasicBlock(nn.Module):
	expansion = 1

	def __init__(self, inplanes, planes, stride=1, downsample=None):
		super(BasicBlock, self).__init__()
		self.conv1 = conv3x3(inplanes, planes, stride)
		self.bn1 = nn.BatchNorm2d(planes)
		self.relu = nn.ReLU(inplace=True)
		self.conv2 = conv3x3(planes, planes)
		self.bn2 = nn.BatchNorm2d(planes)
		self.downsample = downsample
		self.stride = stride

	def forward(self, x):
		residual = x

		out = self.conv1(x)
		out = self.bn1(out)
		out = self.relu(out)

		out = self.conv2(out)
		out = self.bn2(out)

		if self.downsample is not None:
			residual = self.downsample(x)

		out += residual
		out = self.relu(out)

		return out


class Bottleneck(nn.Module):
	expansion = 4

	def __init__(self, inplanes, planes, stride=1, downsample=None):
		super(Bottleneck, self).__init__()
		self.conv1 = conv1x1(inplanes, planes)
		self.bn1 = nn.BatchNorm2d(planes)
		self.conv2 = conv3x3(planes, planes, stride)
		self.bn2 = nn.BatchNorm2d(planes)
		self.conv3 = conv1x1(planes, planes * self.expansion)
		self.bn3 = nn.BatchNorm2d(planes * self.expansion)
		self.relu = nn.ReLU(inplace=True)
		self.downsample = downsample
		self.stride = stride

	def forward(self, x):
		residual = x

		out = self.conv1(x)
		out = self.bn1(out)
		out = self.relu(out)

		out = self.conv2(out)
		out = self.bn2(out)
		out = self.relu(out)

		out = self.conv3(out)
		out = self.bn3(out)

		if self.downsample is not None:
			residual = self.downsample(x)

		out += residual
		out = self.relu(out)

		return out


class ResNet(nn.Module):

	def __init__(self, block, layers, num_classes=1000):
		super(ResNet, self).__init__()
		self.inplanes = 64
		self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
							   bias=False)
		self.bn1 = nn.BatchNorm2d(64)
		self.relu = nn.ReLU(inplace=True)
		self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
		self.layer1 = self._make_layer(block, 64, layers[0])
		self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
		self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
		self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
		self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
		self.fc = nn.Linear(512 * block.expansion, num_classes)

		for m in self.modules():
			if isinstance(m, nn.Conv2d):
				nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
			elif isinstance(m, nn.BatchNorm2d):
				nn.init.constant_(m.weight, 1)
				nn.init.constant_(m.bias, 0)

	def _make_layer(self, block, planes, blocks, stride=1):
		downsample = None
		if stride != 1 or self.inplanes != planes * block.expansion:
			downsample = nn.Sequential(
				conv1x1(self.inplanes, planes * block.expansion, stride),
				nn.BatchNorm2d(planes * block.expansion),
			)

		layers = []
		layers.append(block(self.inplanes, planes, stride, downsample))
		self.inplanes = planes * block.expansion
		for _ in range(1, blocks):
			layers.append(block(self.inplanes, planes))

		return nn.Sequential(*layers)

	def forward(self, x):
		x = self.conv1(x)
		x = self.bn1(x)
		x = self.relu(x)
		x = self.maxpool(x)

		x = self.layer1(x)
		x = self.layer2(x)
		x = self.layer3(x)
		x = self.layer4(x)

		x = self.avgpool(x)
		x = x.view(x.size(0), -1)
		x = self.fc(x)

		return x


def resnet18(pretrained=False, **kwargs):
	"""Constructs a ResNet-18 model.
	Args:
		pretrained (bool): If True, returns a model pre-trained on ImageNet
	"""
	model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
	if pretrained:
		model.load_state_dict(model_zoo.load_url(model_urls['resnet18']))
	return model


def resnet34(pretrained=False, **kwargs):
	"""Constructs a ResNet-34 model.
	Args:
		pretrained (bool): If True, returns a model pre-trained on ImageNet
	"""
	model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
	if pretrained:
		model.load_state_dict(model_zoo.load_url(model_urls['resnet34']))
	return model


def resnet50(pretrained=False, **kwargs):
	"""Constructs a ResNet-50 model.
	Args:
		pretrained (bool): If True, returns a model pre-trained on ImageNet
	"""
	model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
	if pretrained:
		print("=> using pre-trained model '{}'".format('resnet_50'))
		pretrained_state = model_zoo.load_url(model_urls['resnet50'])
		model_state = model.state_dict()
		pretrained_state = { k:v for k,v in pretrained_state.items() if k in model_state and v.size() == model_state[k].size() }
		model_state.update(pretrained_state)
		model.load_state_dict(model_state)
	return model


def resnet101(pretrained=False, **kwargs):
	"""Constructs a ResNet-101 model.
	Args:
		pretrained (bool): If True, returns a model pre-trained on ImageNet
	"""
	model = ResNet(Bottleneck, [3, 4, 23, 3], **kwargs)
	if pretrained:
		model.load_state_dict(model_zoo.load_url(model_urls['resnet101']))
	return model


def resnet152(pretrained=False, **kwargs):
	"""Constructs a ResNet-152 model.
	Args:
		pretrained (bool): If True, returns a model pre-trained on ImageNet
	"""
	model = ResNet(Bottleneck, [3, 8, 36, 3], **kwargs)
	if pretrained:
		model.load_state_dict(model_zoo.load_url(model_urls['resnet152']))
	return model


if __name__ == '__main__':
	net = resnet50(pretrained = True, num_classes = 10)

	raise Exception('halt')
	args = arg()
	training_tool = training_toolset()
	#dataset, dataset_arr = training_tool.initialize_dataset()
	dataset = training_tool.initialize_dataset()
	#training_tool.show_random_sample(dataset_arr, 4)

	batch_size = 2

	trainloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size,
											 shuffle=True, num_workers=4)

	net = fasNet(num_classes = 16, init_weights = False)
	#net = VGG16(num_classes = 16, init_weights = False)
	#net = net.float()
	#summary(net, (3, 224, 224))

	#criterion = nn.L1Loss()
	regression_loss = nn.MSELoss()
	#softmax_loss = nn.sof
	BCE_loss = nn.BCELoss()
	CE_loss = nn.CrossEntropyLoss()
	optimizer = optim.SGD(net.parameters(), lr=0.0001, momentum=0.8)

	count = 0
	epochs = 1
	times = 10000

	for epoch in range(epochs):  # loop over the dataset multiple times
		running_loss = 0.0
		start_time = time.time()
		for i, data in enumerate(trainloader):
			#print('sample', time.time() - start_time)
			start_time = time.time()
			count+=1
			print(count)

			inputs, landmarks, visibility, attributes, category = data['image'], data['landmarks'], data['visibility'], data['attributes'], data['category']
			inputs = inputs.float()
			landmarks = landmarks.float()
			visibility = visibility.float()
			attributes = attributes.type(torch.FloatTensor)
			category = category.type(torch.LongTensor)

			#print('input',time.time() - start_time)
			start_time = time.time()

			optimizer.zero_grad()
			landmarks_out, feature, category_attributes = net(inputs)
			category_out = category_attributes[:, 0:50]
			attributes_out = category_attributes[:, 50:]
			#category_out = category_out.type(torch.LongTensor)
			#attributes_out = attributes_out.type(torch.LongTensor)

			print('forward',time.time() - start_time)
			start_time = time.time()
			'''
			for i in range(batch_size):
				for j in range(8):								# number of total landmarks
					if visibility[i][j] == 0:
						landmarks[i][j][0] = outputs[i][2*j]
						landmarks[i][j][1] = outputs[i][2*j+1]
			'''

			labels = torch.rand(batch_size, 16, requires_grad = False)
			for i in range(batch_size):
				for j in range(8):
					labels[i][2*j] = landmarks[i][j][0]
					labels[i][2*j+1] = landmarks[i][j][1]
			#print('label', time.time() - start_time)
			start_time = time.time()

			landmarks_loss = regression_loss(landmarks_out, labels)
			category_loss = CE_loss(category_out, torch.max(category,1)[1])
			attributes_loss = BCE_loss(attributes_out, attributes)

			if count%2 == 0:
				local_wght = 0.2
				global_wght = 0.8
			else:
				local_wght = 0.8
				global_wght = 0.2

			loss = landmarks_loss*local_wght + (category_loss+attributes_loss)*global_wght


			#print('loss',time.time() - start_time)
			start_time = time.time()

			loss.backward()

			print('back',time.time() - start_time)
			start_time = time.time()

			optimizer.step()

			#print('step',time.time() - start_time)
			start_time = time.time()

			running_loss += loss.item()
			#print('running_loss')
			if count % times == times-1:	# print every 2000 mini-batches
				print('[%d, %d] loss: %.3f' %
					  (epoch + 1, count + 1, running_loss / 200))
				running_loss = 0.0

			if count%100 == 0:
				torch.save(net.state_dict(), 'fasNet_1_{}.pt'.format(count))
				print('{}saved'.format(count))

			if count == times:
				break
		if count == times:
			break
