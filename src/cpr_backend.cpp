//
// Created by Advik on 22-10-2024.
//
#ifdef USE_CPR
#include <z-library/backend/cpr_backend.hpp>
// #include <cpr/cpr.h>
#include <cpr/response.h>
#include <cpr/api.h>

namespace z_library {

    std::string cpr_backend::get_data(const std::string &url) {
        cpr::Response r = Get(cpr::Url{url});
        return r.text;
    }
}
#endif //USE_CPR