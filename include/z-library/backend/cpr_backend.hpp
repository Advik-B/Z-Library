//
// Created by Advik on 22-10-2024.
//

#ifndef CPR_BACKEND_HPP
#define CPR_BACKEND_HPP
#ifdef USE_CPR

#include <string>
#include <z-library/backend/z-backend-scaffold.hpp>

namespace z_library {
    // CPR Backend which inherits from z_cache
    class CPR_backend : z_backend_scaffold {
    public:
        std::string get_data(const std::string &url);

        // Default Constructor, (do not delete)
    };
}

#endif //CPR_BACKEND_HPP
#endif //USE_CPR