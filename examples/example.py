# import baseline model and preprocessor
from anomaly_detection import Preprocessor, SequenceAnomalyModel

##############################################################################
#                                 Load data                                  #
##############################################################################

# Create preprocessor for loading data
preprocessor = Preprocessor(
    length  = 20,           # Extract sequences of 20 items
    timeout = float('inf'), # Do not include a maximum allowed time between events
)

# Load data from csv file
X, y, label, mapping = preprocessor.csv("<path/to/file.csv>")
# Load data from txt file
X, y, label, mapping = preprocessor.text("<path/to/file.txt>")

##############################################################################
#                             Baseline Sequence Model                         #
##############################################################################

# Create baseline sequence model
model = SequenceAnomalyModel(
    input_size  = 300, # Number of different events to expect
    hidden_size = 64 , # Hidden dimension, we suggest 64
    output_size = 300, # Number of different events to expect
)

# Optionally cast data and model to cuda, if available
model   = model  .to("cuda")
X       = X      .to("cuda")
y       = y      .to("cuda")

# Train model
model.fit(
    X          = X,
    y          = y,
    epochs     = 10,
    batch_size = 128,
)

# Predict using the model
y_pred, confidence = model.predict(
    X = X,
    k = 3,
)
