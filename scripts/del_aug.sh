cd ../data/raw || exit
# remove any file whose name contains _aug_ followed by 1–9 or 10+
find . -type f -regex '.*_aug_[1-9][0-9]*\..*' -delete
