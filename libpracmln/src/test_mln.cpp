#include <string>
#include <vector>
#include <iostream>

#include <pracmln/mln.h>
#include <Python.h>

#define MLN_FILE PROJECT_SRC_DIR ".mln"
#define DB_FILE PROJECT_SRC_DIR ".db"

#define TEST_EXT(EXPR, MSG, ONFAIL) if(!(EXPR)) {ONFAIL; std::cout << "FAILED" << std::endl << __LINE__ << ": " << MSG << std::endl << std::flush; return false;}
#define TEST(EXPR, MSG) TEST_EXT(EXPR, MSG, )

bool testMultipleInstances()
{
  std::cout << __func__ << ": " << std::flush;

  TEST(!Py_IsInitialized(), "python is already initialized");

  MLN *mln1, *mln2;
  mln1 = new MLN();
  TEST_EXT(mln1->initialize(), "could not initialize mln", delete mln1);
  TEST_EXT(Py_IsInitialized(), "python is not initialized", delete mln1);

  delete mln1;

  mln1 = new MLN();
  mln2 = new MLN();

  TEST_EXT(mln1->initialize(), "could not initialize mln", delete mln1; delete mln2);
  TEST_EXT(mln2->initialize(), "could not initialize mln", delete mln1; delete mln2);

  delete mln1;
  delete mln2;

  std::cout << "OK" << std::endl << std::flush;
  return true;
}

bool testInitialized()
{
  std::cout << __func__ << ": " << std::flush;

  MLN mln;
  try
  {
    mln.getLogic();
    TEST(false, "mln not initialized but no exception was thrown");
  }
  catch(const char *msg)
  {
  }

  try
  {
    TEST(mln.initialize(), "could not initialize mln");
    mln.getLogic();
  }
  catch(const char *msg)
  {
    TEST(false, "mln initialized but exception was thrown");
  }

  std::cout << "OK" << std::endl << std::flush;
  return true;
}

bool testSettings()
{
  std::cout << __func__ << ": " << std::flush;

  MLN mln;
  TEST(mln.initialize(), "could not initialize mln");

  std::vector<std::string> vec;

  vec = mln.getMethods();
  for(size_t i = 0; i < vec.size(); ++i)
  {
    TEST(mln.setMethod(vec[i]), "could not set method");
    TEST(vec[i] == mln.getMethod(), "method was not set");
  }

  vec = mln.getLogics();
  for(size_t i = 0; i < vec.size(); ++i)
  {
    TEST(mln.setLogic(vec[i]), "could not set logic");
    TEST(vec[i] == mln.getLogic(), "logic was not set");
  }

  vec = mln.getGrammars();
  for(size_t i = 0; i < vec.size(); ++i)
  {
    TEST(mln.setGrammar(vec[i]), "could not set grammar");
    TEST(vec[i] == mln.getGrammar(), "grammar was not set");
  }

  mln.setMLN(MLN_FILE);
  TEST(MLN_FILE == mln.getMLN(), "mln was not set");

  mln.setDB(DB_FILE);
  TEST(DB_FILE == mln.getDB(), "db file was not set");

  mln.setDB("TEST", false);
  TEST("TEST" == mln.getDB(), "db text was not set");

  std::vector<std::string> test;
  test.push_back("TEST");

  mln.setCWPreds(test);
  TEST(test[0] == mln.getCWPreds()[0], "cw preds was not set");

  mln.setQuery(test);
  TEST(test[0] == mln.getQuery()[0], "query was not set");

  mln.setMaxSteps(5);
  TEST(5 == mln.getMaxSteps(), "max steps was not set");

  mln.setMaxSteps(0);
  TEST(-1 == mln.getMaxSteps(), "max steps was not unset");

  mln.setNumChains(5);
  TEST(5 == mln.getNumChains(), "num chains was not set");

  mln.setNumChains(0);
  TEST(-1 == mln.getNumChains(), "num chains was not unset");

  mln.setUseMultiCPU(true);
  TEST(mln.getUseMultiCPU(), "use multi cpu was not set");

  mln.setUseMultiCPU(false);
  TEST(!mln.getUseMultiCPU(), "use multi cpu was not unset");

  std::cout << "OK" << std::endl << std::flush;
  return true;
}

bool testInfer()
{
  std::cout << __func__ << ": " << std::flush;

  MLN mln;
  TEST(mln.initialize(), "could not initialize mln");

  std::vector<std::string> preds;
  preds.push_back(""); // TODO
  std::vector<std::string> query;
  query.push_back(""); // TODO

  mln.setCWPreds(preds);
  mln.setQuery(query);
  mln.setMLN(MLN_FILE); // TODO
  mln.setDB(DB_FILE); // TODO

  std::vector<std::string> results;
  std::vector<double> probabilities;

  TEST(mln.infer(results, probabilities), "mln infer not working");

  std::cout << "OK" << std::endl << std::flush;
  return true;
}

int main(int argc, char **argv)
{
  testMultipleInstances();
  testInitialized();
  testSettings();
  //testInfer();
  return 0;
}
