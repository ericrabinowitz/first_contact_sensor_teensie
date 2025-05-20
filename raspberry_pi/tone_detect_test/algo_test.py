#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["arlpy", "fastgoertzel", "numpy"]
# ///

# Install
# wget -qO- https://astral.sh/uv/install.sh | sh

# Execute
# ./algo_test.py

import arlpy
import fastgoertzel as G
import numpy as np


# Issues
# scipy.signal.goertzel doesn't seem to exist in the scipy versions I checked.
#
# I'm trying to compare fastgoertzel (fast Rust-based lib) to arlpy, a pure
# python lib. The output doesn't match but it seems to work.
#
# How to format the desired freq for the fastgoertzel library? The lib doesn't
# support sample_rate, so I think we need to normalize it somehow.
#
# It might be worth switching directly to DFFT and getting a range of freqs.
# DFFT is a lot more popular and may be just as fast for multiple tone freqs.
# Good option: https://pyfftw.readthedocs.io/en/latest/source/tutorial.html

# ### Reference docs
# https://pypi.org/project/fastgoertzel/
# https://github.com/0zean/fastgoertzel/blob/master/src/lib.rs
# https://arlpy.readthedocs.io/en/latest/signal.html
# https://github.com/org-arl/arlpy/blob/master/arlpy/signal.py#L398
# https://www.embedded.com/the-goertzel-algorithm/


tone_freq = 10000
# TOUCH_THRESHOLD = 0.1

duration = 0.1  # seconds
sample_rate = 44100
# phase = 0

t1 = np.linspace(0, duration, int(sample_rate * duration), False)
tone1 = np.sin(2 * np.pi * tone_freq * t1)
tone1.astype(np.float32, copy=False)

t2 = np.arange(0, int(sample_rate * duration))
tone_freq2 = tone_freq / sample_rate
tone2 = np.sin(2 * np.pi * tone_freq2 * t2)
tone2.astype(np.float64, copy=False)

amp1 = arlpy.signal.goertzel(tone_freq, tone1, sample_rate)
print("arlpy:", amp1)

amp2, phase2 = G.goertzel(tone2, tone_freq2)
print("fastgoertzel:", amp2, phase2)
