# EEG-Vision: Deep Learning for Generalized EEG-based Image Visualization
A Deep Learning project aimed to improve SOTA in EEG-based Image Visualization.

A research project at Carnegie Mellon University by:
<ul>
  <li>Stefan Baumann - sbaumann@andrew.cmu.edu</li>
  <li>Ammar Karkour - akarkour@andrew.cmu.edu</li>
  <li>Sideeg Hassan - sahassan@andrew.cmu.edu</li>
  <li>EuiSuh Jeong - esj1@cmu.edu</li>
</ul>

# Abstract
The human brain is one of the biggest mysteries that scientists have been studying and trying to
understand for centuries. and a big part of this research is studying how different types of inputs affect
the brain activity, and this is why understanding how the human brain perceives visual inputs is
considered one of the main goals of this research area. Historically, understanding visual perception
has been done through brain anatomy and cognitive psychology, but recently the rapid increase in the
amount of brain signals data available on the Internet has provided the opportunity for researchers
to use deep learning techniques to simulate and reconstruct how our brains perceive visual inputs
(i.e., images), with the goal of classifying brain signals of visual inputs to image classes. Several
attempts were made to solve this problem using EEG brain signals, such as PeRCeiVe Lab who used
a CNN based EEG features extraction model with an accuracy of 48.1% on classification tasks. In
this project, we improve on their work using a BiLSTM based features extraction model (EEG-Net)
that achieves a better accuracy of 53% on classification of PeRCeiVe Lab’s dataset. Moreover, we
use a pre-trained Image-Net to extract image features, which are used later along with the EEG
features extracted from EEG-Net to train a third mapping model (EEG-Image-Map) that takes in
an EEG features vector as an input and returns an image features vector as an output, in an attempt
to visualize images that were not part of our training classes, which to our knowledge was not done
before.

Google drive folder containing the datasets used: 
https://drive.google.com/drive/folders/11rbCEBVtssmyh3rFFNtU4HeIcmdM3XJB?usp=sharing
