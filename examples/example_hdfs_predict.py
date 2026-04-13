# Import pytorch
import torch

# Import baseline model and preprocessor
from anomaly_detection import Preprocessor, SequenceAnomalyModel

# Imports for showing metrics
import numpy as np
from sklearn.metrics import classification_report

##############################################################################
#                                 Load data                                  #
##############################################################################

# Create preprocessor for loading data
preprocessor = Preprocessor(
    length  = 20,           # Extract sequences of 20 items
    timeout = float('inf'), # Do not include a maximum allowed time between events
)

# Load normal data from HDFS dataset
X, y, label, mapping = preprocessor.text(
    path    = "./data/hdfs_test_normal",
    verbose = True,
    # nrows   = 10_000, # Uncomment/change this line to only load a limited number of rows
)

# Split in train test data (20:80 ratio)
X_train = X[:X.shape[0]//5 ]
X_test  = X[ X.shape[0]//5:]
y_train = y[:y.shape[0]//5 ]
y_test  = y[ y.shape[0]//5:]

##############################################################################
#                             Baseline Sequence Model                         #
##############################################################################

# Create baseline model object
model = SequenceAnomalyModel(
    input_size  = 30, # Number of different events to expect
    hidden_size = 64, # Hidden dimension, we suggest 64
    output_size = 30, # Number of different events to expect
)

# Optionally cast data and model to cuda, if available
if torch.cuda.is_available():
    # Set model to device
    model = model.to("cuda")

    # Set data to device
    X_train = X_train.to("cuda")
    y_train = y_train.to("cuda")
    X_test  = X_test .to("cuda")
    y_test  = y_test .to("cuda")

# Train model
model.fit(
    X          = X_train,
    y          = y_train,
    epochs     = 10,
    batch_size = 128,
    optimizer  = torch.optim.Adam,
)

# Predict normal data using the baseline model
y_pred, confidence = model.predict(
    X = X_test,
    k = 3, # Change this value to get the top k predictions
)

################################################################################
#                            Classification report                             #
################################################################################

# Transform to numpy for classification report
y_true = y_test.cpu().numpy()
y_pred = y_pred.cpu().numpy()

# Set prediction to "most likely" prediction
prediction = y_pred[:, 0]
# In case correct prediction was in top k, set prediction to correct prediction
for column in range(1, y_pred.shape[1]):
    # Get mask where prediction in given column is correct
    mask = y_pred[:, column] == y_true
    # Adjust prediction
    prediction[mask] = y_true[mask]

# Show classification report
print(classification_report(
    y_true = y_true,
    y_pred = prediction,
    digits = 4,
    zero_division = 0,
))
