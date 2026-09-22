/**
 * @file linearSearch.cpp
 * @brief
 * @author jiachang (jiachanggit@gmail.com)
 * @version 1.4
 * @date 2024-02-11
 *
 * @copyright Copyright (c) 2024  JIA-CHANG
 *
 * @par dialog:
 * <table>
 * <tr><th>Date       <th>Version <th>Author  <th>Description
 * <tr><td>2024-02-11 <td>1.4     <td>jiachang     <td>brutely linear search
 * </table>
 */

#include "linearSearch.hpp"

std::vector<int> LinearSearch::search(std::vector<Rule5D> &rule5V,
                          const std::vector<Packet5D> &packet5V) {
  const char *LinearSearch_path = "./INFO/LinearSearch_FaultPacket5D_test.txt";
  std::ofstream outFile(LinearSearch_path);
  std::vector<int> matchedIndex(packet5V.size(), -1);
  bool isBreak = false;
  size_t i = 0;
  for (const auto &packet : packet5V) {
    for (auto &rule : rule5V) {
      if (rule.isMatch(packet)) {
        ++packetCounter;
        // rule.pri is 1-indexed (see io/input.cpp); normalize to the
        // 0-indexed line number pipeline/classbench_io.py uses as priority.
        matchedIndex[i] = static_cast<int>(rule.pri) - 1;
        isBreak = true;
        break;
      }
    }
    if (!isBreak) {
      outFile << "Source IP: " << unsigned(packet.ipS32) << "\n";
      outFile << "Destination IP: " << unsigned(packet.ipD32) << "\n";
      outFile << "Source Port: " << unsigned(packet.portS) << "\n";
      outFile << "Destination Port: " << unsigned(packet.portD) << "\n";
      outFile << "Protocol: 0x" << std::hex << unsigned(packet.protocol)
              << std::dec << "\n";
      outFile << "\n";
    }
    isBreak = false;
    ++i;
  }
  outFile << "LinearSearch.packetCounter = " << packetCounter << "\n";
  outFile.close();
  std::cout << "LinearSearch.packetCounter = " << packetCounter << "\n";
  return matchedIndex;
};
