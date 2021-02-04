# -*- coding: utf-8 -*-
"""yes or no.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1t4BhcCc9grfVWQr9SFTBe-OYBbXgmfKN
"""

import os
!pip install urllib3==1.25.10
import urllib3
import urllib.request

!pip install torch torchvision
!pip install transformers==2.5.1
!pip install pandas
!pip install numpy
!gsutil cp gs://boolq/train.jsonl .
!gsutil cp gs://boolq/dev.jsonl .

import random
import torch
import numpy as np
import pandas as pd
from tqdm import tqdm
import botocore
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AdamW

# Use a GPU if you have one available (Runtime -> Change runtime type -> GPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Set seeds for reproducibility
random.seed(26)
np.random.seed(26)
torch.manual_seed(26)

tokenizer = AutoTokenizer.from_pretrained("roberta-base") 

model = AutoModelForSequenceClassification.from_pretrained("roberta-base")
model.to(device) # Send the model to the GPU if we have one

learning_rate = 1e-5
optimizer = AdamW(model.parameters(), lr=learning_rate, eps=1e-8)

def encode_data(tokenizer, questions, passages, max_length):
    """Encode the question/passage pairs into features than can be fed to the model."""
    input_ids = []
    attention_masks = []

    for question, passage in zip(questions, passages):
        encoded_data = tokenizer.encode_plus(question, passage, max_length=max_length, pad_to_max_length=True, truncation_strategy="longest_first")
        encoded_pair = encoded_data["input_ids"]
        attention_mask = encoded_data["attention_mask"]

        input_ids.append(encoded_pair)
        attention_masks.append(attention_mask)

    return np.array(input_ids), np.array(attention_masks)

# Loading data english
train_data_df = pd.read_json("/content/trainfr.jsonl", lines=True, orient='records')
dev_data_df = pd.read_json("/content/devfr.jsonl", lines=True, orient="records")

passages_train = train_data_df.passage.values
questions_train = train_data_df.question.values
answers_train = train_data_df.answer.values.astype(int)

passages_dev = dev_data_df.passage.values
questions_dev = dev_data_df.question.values
answers_dev = dev_data_df.answer.values.astype(int)

# Encoding data
max_seq_length = 256
input_ids_train, attention_masks_train = encode_data(tokenizer, questions_train, passages_train, max_seq_length)
input_ids_dev, attention_masks_dev = encode_data(tokenizer, questions_dev, passages_dev, max_seq_length)

train_features = (input_ids_train, attention_masks_train, answers_train)
dev_features = (input_ids_dev, attention_masks_dev, answers_dev)

def encode_data(tokenizer, questions, passages, max_length):
    """Encode the question/passage pairs into features than can be fed to the model."""
    input_ids = []
    attention_masks = []

    for question, passage in zip(questions, passages):
        encoded_data = tokenizer.encode_plus(question, passage, max_length=max_length, pad_to_max_length=True, truncation_strategy="longest_first")
        encoded_pair = encoded_data["input_ids"]
        attention_mask = encoded_data["attention_mask"]

        input_ids.append(encoded_pair)
        attention_masks.append(attention_mask)

    return np.array(input_ids), np.array(attention_masks)

# Loading data french
train_data_df1 = pd.read_json("/content/trainfr.jsonl", lines=True, orient='records')
dev_data_df1 = pd.read_json("/content/devfr.jsonl", lines=True, orient="records")

passages_train1 = train_data_df1.passage.values
questions_train1 = train_data_df1.question.values
answers_train1 = train_data_df1.answer.values.astype(int)

passages_dev1 = dev_data_df1.passage.values
questions_dev1 = dev_data_df1.question.values
answers_dev1 = dev_data_df1.answer.values.astype(int)

# Encoding data
max_seq_length = 256
input_ids_train1, attention_masks_train1 = encode_data(tokenizer, questions_train1, passages_train1, max_seq_length)
input_ids_dev1, attention_masks_dev1 = encode_data(tokenizer, questions_dev1, passages_dev1, max_seq_length)

train_features1 = (input_ids_train1, attention_masks_train1, answers_train1)
dev_features1 = (input_ids_dev1, attention_masks_dev1, answers_dev1)

#french
batch_size = 32

train_features_tensors1 = [torch.tensor(feature, dtype=torch.long) for feature in train_features1]
dev_features_tensors1 = [torch.tensor(feature, dtype=torch.long) for feature in dev_features1]

train_dataset1 = TensorDataset(*train_features_tensors1)
dev_dataset1 = TensorDataset(*dev_features_tensors1)

train_sampler1 = RandomSampler(train_dataset1)
dev_sampler1 = SequentialSampler(dev_dataset1)

train_dataloader1 = DataLoader(train_dataset1, sampler=train_sampler1, batch_size=batch_size)
dev_dataloader1 = DataLoader(dev_dataset1, sampler=dev_sampler1, batch_size=batch_size)

#english
batch_size = 32

train_features_tensors = [torch.tensor(feature, dtype=torch.long) for feature in train_features]
dev_features_tensors = [torch.tensor(feature, dtype=torch.long) for feature in dev_features]

train_dataset = TensorDataset(*train_features_tensors)
dev_dataset = TensorDataset(*dev_features_tensors)

train_sampler = RandomSampler(train_dataset)
dev_sampler = SequentialSampler(dev_dataset)

train_dataloader = DataLoader(train_dataset, sampler=train_sampler, batch_size=batch_size)
dev_dataloader = DataLoader(dev_dataset, sampler=dev_sampler, batch_size=batch_size)

epochs = 50
grad_acc_steps = 1
train_loss_values = []
dev_acc_values = []

for _ in tqdm(range(epochs), desc="Epoch"):

  # Training
  epoch_train_loss = 0 # Cumulative loss
  model.train()
  model.zero_grad()

  for step, batch in enumerate(train_dataloader):

      input_ids = batch[0].to(device)
      attention_masks = batch[1].to(device)
      labels = batch[2].to(device)     

      outputs = model(input_ids, token_type_ids=None, attention_mask=attention_masks, labels=labels)

      loss = outputs[0]
      loss = loss / grad_acc_steps
      epoch_train_loss += loss.item()

      loss.backward()
      
      if (step+1) % grad_acc_steps == 0: # Gradient accumulation is over
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0) # Clipping gradients
        optimizer.step()
        model.zero_grad()

  epoch_train_loss = epoch_train_loss / len(train_dataloader)          
  train_loss_values.append(epoch_train_loss)
  
  # Evaluation
  epoch_dev_accuracy = 0 # Cumulative accuracy
  model.eval()

  for batch in dev_dataloader:
    
    input_ids = batch[0].to(device)
    attention_masks = batch[1].to(device)
    labels = batch[2]
                
    with torch.no_grad():        
        outputs = model(input_ids, token_type_ids=None, attention_mask=attention_masks)
                    
    logits = outputs[0]
    logits = logits.detach().cpu().numpy()
    
    predictions = np.argmax(logits, axis=1).flatten()
    labels = labels.numpy().flatten()
    
    epoch_dev_accuracy += np.sum(predictions == labels) / len(labels)

  epoch_dev_accuracy = epoch_dev_accuracy / len(dev_dataloader)
  dev_acc_values.append(epoch_dev_accuracy)
#torch.save(model, "/content/save.h5") 
data = {
"model_state": model.state_dict()
}

FILE = "data.pth"
torch.save(data, FILE)

print(f'training complete. file saved to {FILE}')
data = torch.load(FILE)

FILE1 = "/content/drive/MyDrive/Colab Notebooks/datafr2.pth"
data1 = torch.load(FILE1)

model_state1 = data1["model_state"]

model.load_state_dict(model_state1)
model.eval()

FILE = "/content/drive/MyDrive/Colab Notebooks/data.pth"
data = torch.load(FILE)

model_state = data["model_state"]

model.load_state_dict(model_state)
model.eval()

from google.colab import drive
drive.mount('/content/drive')

drive.flush_and_unmount()
print('All changes made in this colab session should now be visible in Drive.')

def predict(question, passage):
  sequence = tokenizer.encode_plus(question, passage, return_tensors="pt")['input_ids'].to(device)
  
  logits = model(sequence)[0]
  probabilities = torch.softmax(logits, dim=1).detach().cpu().tolist()[0]
  proba_yes = round(probabilities[1], 2)
  proba_no = round(probabilities[0], 2)

  print(f"Question: {question}, Oui: {proba_yes}, Non: {proba_no}")
  
passage_superbowl = """Montbéliard (prononciation : /mɔ̃.be.li.aʁ/) est une commune de l'Est de la France, sous-préfecture du département du Doubs en région Bourgogne-Franche-Comté. Elle est située dans le nord-est de la Franche-Comté historique, à moins d'une vingtaine de kilomètres de la Suisse, aux portes du massif du Jura. Montbéliard et sa proche région (le « Pays de Montbéliard ») n'ont été rattachés à la France qu'en 1793."""
 
passage_illuin = """Illuin designs and builds solutions tailored to your strategic needs using Artificial Intelligence
                  and the new means of human interaction this technology enables."""

superbowl_questions = [
                       
"Montbéliard est-elle en France?"

]

####est-ce-que Montbéliard est en France ? NoN

for s_question in superbowl_questions:
  predict(s_question, passage_superbowl)