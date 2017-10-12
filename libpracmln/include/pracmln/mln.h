#ifndef __MLN_H__
#define __MLN_H__

// STL
#include <string>
#include <vector>

class MLN{
private:
  struct Internal;
  Internal *internal;

  std::vector<std::string> methods;

  size_t method;
  size_t logic;
  size_t grammar;

  std::string mln;
  std::string db;

  bool initialized;
  bool dbIsFile;
  bool updateDB;
  bool updateMLN;

public:
  MLN();
  virtual ~MLN();

  bool initialize();

  std::vector<std::string> getMethods() const;
  std::vector<std::string> getLogics() const;
  std::vector<std::string> getGrammars() const;

  bool setMethod(const std::string &method);
  bool setLogic(const std::string &logic);
  bool setGrammar(const std::string &grammar);
  void setMLN(const std::string &mln);
  void setDB(const std::string &db, const bool isFile = true);
  void setQuery(const std::vector<std::string> &query);

  std::string getMethod() const;
  std::string getLogic() const;
  std::string getGrammar() const;
  std::string getMLN() const;
  std::string getDB() const;
  std::vector<std::string> getQuery() const;

  void setCWPreds(const std::vector<std::string> &cwPreds);
  void setMaxSteps(const int value);
  void setNumChains(const int value);
  void setUseMultiCPU(const bool enable);

  std::vector<std::string> getCWPreds() const;
  int getMaxSteps() const;
  int getNumChains() const;
  bool getUseMultiCPU() const;

  bool infer(std::vector<std::string> &results, std::vector<double> &probabilities);

private:
  bool init();

  bool isInOptions(const std::string &option, const std::vector<std::string> &options, size_t &value) const;
};

#endif //__MLN_H__
