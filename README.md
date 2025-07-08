# Food or not-Food Classifier

In this classifier, a model was built with PyTorch to classify images into two categories: food and not-food.

## Dataset:
The following datasets were used:
- [Food-5K](https://www.kaggle.com/datasets/trolukovich/food5k-image-dataset)
- [Food or not dataset](https://www.kaggle.com/datasets/sciencelabwork/food-or-not-dataset)

Both of them don't have the same structure so there is a [script](src/data_prep.py) that will clean and prepare the data for training.
Just paste the folders into the `data/raw` folder and run the script. \
Make sure that your file structure is like this:
```
.
└── raw
    ├── food-5k
    │   ├── evaluation
    │   │   ├── food
    │   │   └── non_food
    │   ├── training
    │   │   ├── food
    │   │   └── non_food
    │   └── validation
    │       ├── food
    │       └── non_food
    └── food-or-not-dataset
        ├── test
        │   ├── food_images
        │   └── negative_non_food
        └── train
            ├── food_images
            └── negative_non_food
```
Otherwise: rename the folders accordingly or change the script.

The images in the `food-5k` dataset are named: `xxx.jpg`(e.g. `253.jpg`).
So they need to be sorted based on their directory-names.

The images in the `food-or-not-dataset` are named: `(training|validation|test)_(food|non_food)_xxx_aug_x.jpg` (e.g. `training_food_174_aug_5.jpg`).
So there a bit more organization is needed. The augmented images are not needed, since we will add the augmentation in the training pipeline.
