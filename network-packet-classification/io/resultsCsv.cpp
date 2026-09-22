#include "resultsCsv.hpp"

#include <fstream>

void writeResultsCsv(const std::string &path,
                     const std::vector<int> &matchedIndex) {
  std::ofstream out(path);
  out << "packet_index,matched_priority\n";
  for (size_t i = 0; i < matchedIndex.size(); ++i) {
    out << i << "," << matchedIndex[i] << "\n";
  }
}
