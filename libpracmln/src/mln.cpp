#include <boost/python.hpp>
#include <Python.h>

#include <pracmln/mln.h>
#include <iostream>

/*******************************************************************************
 * Defines
 ******************************************************************************/

#define MODULE_MLN      "pracmln.mln"
#define MODULE_METHODS  "pracmln.mln.methods"
#define MODULE_DATABASE "pracmln.mln.database"
#define MODULE_QUERY    "pracmln.mlnquery"

#define NAME_CW_PREDS   "cw_preds"
#define NAME_MAX_STEPS  "maxsteps"
#define NAME_NUM_CHAINS "chains"
#define NAME_MULTI_CPU  "multicore"
#define NAME_VERBOSE    "verbose"
#define NAME_MERGE_DBS  "mergeDBs"

#define CHECK_INITIALIZED() if(!initialized) throw "MLN is not initiazied!"

using namespace boost;

const std::string logics_array[] = {"FirstOrderLogic", "FuzzyLogic"};
const std::string grammars_array[] = {"StandardGrammar", "PRACGrammar"};

const std::vector<std::string> logics(logics_array, logics_array + sizeof(logics_array) / sizeof(logics_array[0]));
const std::vector<std::string> grammars(grammars_array, grammars_array + sizeof(grammars_array) / sizeof(grammars_array[0]));

/*******************************************************************************
 * Utility
 ******************************************************************************/

template<typename T>
std::vector<T> listToVector(python::list list)
{
  std::vector<T> vec;
  vec.resize(python::len(list));
  for(size_t i = 0; i < vec.size(); ++i)
  {
    vec[i] = python::extract<T>(list[i]);
  }
  return vec;
}

template<typename T>
python::list vectorToList(const std::vector<T> &vec)
{
  python::list list;
  for(size_t i = 0; i < vec.size(); ++i)
  {
    list.append(vec[i]);
  }
  return list;
}

/*******************************************************************************
 * Internal struct
 ******************************************************************************/

struct MLN::Internal
{
  python::object module_mln;
  python::dict dict_mln;

  python::object module_methods;
  python::dict dict_methods;

  python::object module_database;
  python::dict dict_database;

  python::object module_query;
  python::dict dict_query;

  python::object mlnObj;
  python::object mln;
  python::object mlnQueryObj;
  python::object mlnQuery;

  python::object db;
  python::object method;

  python::list query;

  python::dict settings;
};

/*******************************************************************************
 * Initialize
 ******************************************************************************/

MLN::MLN() : internal(NULL), method(0), logic(0), grammar(0), initialized(false), dbIsFile(false), updateDB(false), updateMLN(false)
{
  if(!Py_IsInitialized())
  {
    Py_Initialize();
  }
}

MLN::~MLN()
{
  if(internal)
  {
    delete internal;
  }
}

bool MLN::initialize()
{
  if(initialized)
  {
    return true;
  }
  try
  {
    if(!internal)
    {
      internal = new Internal();
    }

    internal->module_mln = python::import(MODULE_MLN);
    internal->dict_mln = python::extract<python::dict>(internal->module_mln.attr("__dict__"));

    internal->module_methods = python::import(MODULE_METHODS);
    internal->dict_methods = python::extract<python::dict>(internal->module_methods.attr("__dict__"));

    internal->module_database = python::import(MODULE_DATABASE);
    internal->dict_database = python::extract<python::dict>(internal->module_database.attr("__dict__"));

    internal->module_query = python::import(MODULE_QUERY);
    internal->dict_query = python::extract<python::dict>(internal->module_query.attr("__dict__"));

    this->methods = listToVector<std::string>(python::extract<python::list>(internal->dict_methods["InferenceMethods"].attr("ids")()));

    initialized = true;
    setMethod(this->methods[2]);

    internal->settings[NAME_CW_PREDS] = python::list();
    internal->settings[NAME_MULTI_CPU] = false;
    internal->settings[NAME_VERBOSE] = false;
    internal->settings[NAME_MERGE_DBS] = false;
  }
  catch(python::error_already_set)
  {
    PyErr_Print();
    initialized = false;
    return false;
  }
  return true;
}

std::vector<std::string> MLN::getMethods() const
{
  CHECK_INITIALIZED();
  return methods;
}

std::vector<std::string> MLN::getLogics() const
{
  CHECK_INITIALIZED();
  return logics;
}

std::vector<std::string> MLN::getGrammars() const
{
  CHECK_INITIALIZED();
  return grammars;
}

/*******************************************************************************
 * General
 ******************************************************************************/

bool MLN::setMethod(const std::string &method)
{
  CHECK_INITIALIZED();
  const size_t oldValue = this->method;
  if(isInOptions(method, methods, this->method))
  {
    if(oldValue != this->method)
    {
      internal->method = internal->dict_methods["InferenceMethods"].attr("clazz")(this->methods[this->method]);
    }
    return true;
  }
  return false;
}

bool MLN::setLogic(const std::string &logic)
{
  CHECK_INITIALIZED();
  const size_t oldValue = this->logic;
  if(isInOptions(logic, logics, this->logic))
  {
    updateMLN = updateMLN || this->logic != oldValue;
    updateDB = updateMLN;
    return true;
  }
  return false;
}

bool MLN::setGrammar(const std::string &grammar)
{
  CHECK_INITIALIZED();
  const size_t oldValue = this->grammar;
  if(isInOptions(grammar, grammars, this->grammar))
  {
    updateMLN = updateMLN || this->grammar == oldValue;
    updateDB = updateMLN;
    return true;
  }
  return false;
}

void MLN::setMLN(const std::string &mln)
{
  CHECK_INITIALIZED();
  updateMLN = true;
  updateDB = true;
  this->mln = mln;
}

void MLN::setDB(const std::string &db, const bool isFile)
{
  CHECK_INITIALIZED();
  this->db = db;
  dbIsFile = isFile;
  updateDB = true;
}

void MLN::setQuery(const std::vector<std::string> &query)
{
  CHECK_INITIALIZED();
  internal->query = vectorToList(query);
}

std::string MLN::getMethod() const
{
  CHECK_INITIALIZED();
  return methods[method];
}

std::string MLN::getLogic() const
{
  CHECK_INITIALIZED();
  return logics[logic];
}

std::string MLN::getGrammar() const
{
  CHECK_INITIALIZED();
  return grammars[grammar];
}

std::string MLN::getMLN() const
{
  CHECK_INITIALIZED();
  return mln;
}

std::string MLN::getDB() const
{
  CHECK_INITIALIZED();
  return db;
}

std::vector<std::string> MLN::getQuery() const
{
  CHECK_INITIALIZED();
  return listToVector<std::string>(internal->query);
}

/*******************************************************************************
 * Settings
 ******************************************************************************/

void MLN::setCWPreds(const std::vector<std::string> &cwPreds)
{
  CHECK_INITIALIZED();
  internal->settings[NAME_CW_PREDS] = vectorToList(cwPreds);
}

void MLN::setMaxSteps(const int value)
{
  CHECK_INITIALIZED();
  if(value > 0)
  {
    internal->settings[NAME_MAX_STEPS] = value;
  }
  else
  {
    internal->settings[NAME_MAX_STEPS].del();
  }
}

void MLN::setNumChains(const int value)
{
  CHECK_INITIALIZED();
  if(value > 0)
  {
    internal->settings[NAME_NUM_CHAINS] = value;
  }
  else
  {
    internal->settings[NAME_NUM_CHAINS].del();
  }
}

void MLN::setUseMultiCPU(const bool enable)
{
  CHECK_INITIALIZED();
  internal->settings[NAME_MULTI_CPU] = enable;
}

std::vector<std::string> MLN::getCWPreds() const
{
  CHECK_INITIALIZED();
  return listToVector<std::string>(python::extract<python::list>(internal->settings[NAME_CW_PREDS]));
}

int MLN::getMaxSteps() const
{
  CHECK_INITIALIZED();
  if(internal->settings.has_key(NAME_MAX_STEPS))
  {
    return python::extract<int>(internal->settings[NAME_MAX_STEPS]);
  }
  return -1;
}

int MLN::getNumChains() const
{
  CHECK_INITIALIZED();
  if(internal->settings.has_key(NAME_NUM_CHAINS))
  {
    return python::extract<int>(internal->settings[NAME_NUM_CHAINS]);
  }
  return -1;
}

bool MLN::getUseMultiCPU() const
{
  CHECK_INITIALIZED();
  return python::extract<bool>(internal->settings[NAME_MULTI_CPU]);
}

/*******************************************************************************
 * Methods
 ******************************************************************************/

bool MLN::infer(std::vector<std::string> &results, std::vector<double> &probabilities)
{
  CHECK_INITIALIZED();
  try
  {
    if(!init())
    {
      return false;
    }
    //the empty config file
    boost::python::list arguments;

    //the actual config -> for now here, but consider making this a class member
    boost::python::dict settings;
    settings["mln"] = internal->mln;
    settings["db"] = internal->db;
    settings["method"] = internal->method;
    settings["cw_preds"] = internal->settings[NAME_CW_PREDS];
    settings["queries"] = internal->query;

    internal->mlnQueryObj = internal->dict_query["MLNQuery"](*boost::python::tuple(arguments), **settings);
    python::object resObj = internal->mlnQueryObj.attr("run")();
    resObj.attr("write")();
    python::dict resObjDict = python::extract<python::dict>(resObj.attr("results"));
    python::list keys = resObjDict.keys();
    results.resize(python::len(keys));
    probabilities.resize(results.size());

    for(size_t i = 0; i < results.size(); ++i)
    {
      results[i] = python::extract<std::string>(keys[i]);
    }
    std::sort(results.begin(), results.end());

    for(size_t i = 0; i < results.size(); ++i)
    {
      probabilities[i] = python::extract<double>(resObjDict[results[i]]);
    }
  }
  catch(python::error_already_set)
  {
    PyErr_Print();
    return false;
  }
  return true;
}

/*******************************************************************************
 * Private
 ******************************************************************************/

bool MLN::init()
{
  try
  {
    if(updateMLN)
    {
      internal->mlnObj = internal->dict_mln["MLN"];
      internal->mln = internal->mlnObj.attr("load")(mln, logics[logic], grammars[grammar]);
    }

    if(updateDB)
    {
      python::list dbs;
      if(dbIsFile)
      {
        dbs = python::extract<python::list>(internal->dict_database["Database.load"](internal->mln, db));
      }
      else
      {
        dbs = python::extract<python::list>(internal->dict_database["parse_db"](internal->mln, db));
      }
      internal->db = dbs[0];
    }

    updateMLN = false;
    updateDB = false;
  }
  catch(python::error_already_set)
  {
    PyErr_Print();
    return false;
  }
  return true;
}

bool MLN::isInOptions(const std::string &option, const std::vector<std::string> &options, size_t &value) const
{
  for(size_t i = 0; i < options.size(); ++i)
  {
    if(option == options[i])
    {
      value = i;
      return true;
    }
  }
  return false;
}
