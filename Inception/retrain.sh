
directory=../radio_bursts/
sudo python3 retrain.py --image_dir ../radio_bursts/ --validation_batch_size -1 --how_many_training_steps 1500 --random_brightness 5 --print_misclassified_test_images 