#ifndef __IO_RESULTSCSV_HPP__
#define __IO_RESULTSCSV_HPP__

#include <string>
#include <vector>

// Shared by every classifier: writes one row per packet as
// "packet_index,matched_priority" (matched_priority is -1 when unmatched),
// in the same 0-indexed priority convention as pipeline/run_pipeline.py's
// --out CSV so the two can be diffed with pipeline/compare_results.py.
void writeResultsCsv(const std::string &path,
                     const std::vector<int> &matchedIndex);

#endif
