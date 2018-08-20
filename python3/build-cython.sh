
cd pracmln/logic/
echo "======================LOGIC======================"
python3 setup.py build_ext --inplace
echo "================================================="

echo "=======================MLN======================="
cd ../mln/
python3 setup.py build_ext --inplace
echo "================================================="

echo "====================GROUNDING===================="
cd grounding/
python3 setup.py build_ext --inplace
echo "================================================="

echo "====================INFERENCE===================="
cd ../inference/
python3 setup.py build_ext --inplace
echo "================================================="

