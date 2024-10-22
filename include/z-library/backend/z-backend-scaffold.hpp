//
// Created by Advik on 22-10-2024.
//

#ifndef Z_CACHE_HPP
#define Z_CACHE_HPP

#include <string>

namespace z_library {
    class z_backend_scaffold {
    private:
        z_backend_scaffold() = default;
        ~z_backend_scaffold() = default;

        // void set(const std::string &key, const std::string &value);
        // std::string get(const std::string &key);
        // void delete_cache(const std::string &key);
        // void clear_cache();
    public:
        std::string get_data(const std::string &url);
    };
}

#endif //Z_CACHE_HPP
