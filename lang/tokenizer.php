<?php

$tokens = [];

$file = preg_replace("/\s+/", " ", file_get_contents($argv[1]));

echo $file;