# Imports
import argformat
import argparse
import torch
import torch.nn as nn
import warnings

# Package imports
from anomaly_detection import Preprocessor, SequenceAnomalyModel

if __name__ == "__main__":
    ########################################################################
    #                           Parse arguments                            #
    ########################################################################

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog            = "anomaly_detection",
        description     = "Sequence anomaly detection from system logs",
        formatter_class = argformat.StructuredFormatter,
    )

    # Add model mode arguments, run in different modes
    parser.add_argument('mode', help="mode in which to run the sequence model", choices=(
        'train',
        'predict',
    ))

    # Add arguments
    group_input = parser.add_argument_group("Input parameters")
    group_input.add_argument('--csv'      , help="CSV events file to process")
    group_input.add_argument('--txt'      , help="TXT events file to process")
    group_input.add_argument('--length'   , type=int  , default=20          , help="sequence LENGTH           ")
    group_input.add_argument('--timeout'  , type=float, default=float('inf'), help="sequence TIMEOUT (seconds)")

    # Sequence-model parameters
    group_model = parser.add_argument_group("Baseline model parameters")
    group_model.add_argument(      '--hidden', type=int, default=64 , help='hidden dimension')
    group_model.add_argument('-i', '--input' , type=int, default=300, help='input  dimension')
    group_model.add_argument('-l', '--layers', type=int, default=2  , help='number of lstm layers to use')
    group_model.add_argument('-k', '--top'   , type=int, default=1  , help='accept any of the TOP predictions')
    group_model.add_argument('--save', help="save model to specified file")
    group_model.add_argument('--load', help="load model from specified file")

    # Training
    group_training = parser.add_argument_group("Training parameters")
    group_training.add_argument('-b', '--batch-size', type=int, default=128,   help="batch size")
    group_training.add_argument('-d', '--device'    , default='auto'     ,     help="train using given device (cpu|cuda|auto)")
    group_training.add_argument('-e', '--epochs'    , type=int, default=10,    help="number of epochs to train with")

    # Parse given arguments
    args = parser.parse_args()

    ########################################################################
    #                              Load data                               #
    ########################################################################

    # Set device
    if args.device is None or args.device == 'auto':
        args.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Create preprocessor
    preprocessor = Preprocessor(
        length  = args.length,
        timeout = args.timeout,
    )

    # Load files
    if args.csv is not None and args.txt is not None:
        # Raise an error if both csv and txt are specified
        raise ValueError("Please specify EITHER --csv OR --txt.")
    if args.csv:
        # Load csv file
        X, y, label, mapping = preprocessor.csv(args.csv)
    elif args.txt:
        # Load txt file
        X, y, label, mapping = preprocessor.txt(args.txt)

    X = X.to(args.device)
    y = y.to(args.device)

    ########################################################################
    #                         Create Baseline Model                        #
    ########################################################################

    # Load model from file, if necessary
    if args.load:
        model = SequenceAnomalyModel.load(args.load).to(args.device)

    # Otherwise create a new model instance
    else:
        model = SequenceAnomalyModel(
            input_size  = args.input,
            hidden_size = args.hidden,
            output_size = args.input,
            num_layers  = args.layers,
        ).to(args.device)

    # Train model
    if args.mode == "train":

        # Print warning if training without saving output
        if args.save is None:
            warnings.warn("Training the model without saving it to output.")

        # Train model
        model.fit(
            X             = X,
            y             = y,
            epochs        = args.epochs,
            batch_size    = args.batch_size,
            criterion     = nn.CrossEntropyLoss(),
        )

        # Save model to file
        if args.save:
            model.save(args.save)

    # Predict with model
    if args.mode == "predict":

        # Predict using the model
        y_pred, confidence = model.predict(
            X = X,
            k = args.top,
        )

        ####################################################################
        #                        Top-k Prediction Logic                    #
        ####################################################################

        # Initialise predictions
        y_pred_top = y_pred[:, 0]
        # Compute top TOP predictions
        for top in range(1, args.top):
            # Get mask
            mask = y == y_pred[:, top]
            # Set top values
            y_pred_top[mask] = y[mask]

        from sklearn.metrics import classification_report
        print(classification_report(y.cpu(), y_pred_top.cpu(), digits=4))
