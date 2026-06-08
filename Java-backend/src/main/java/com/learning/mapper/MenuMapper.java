package com.learning.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.learning.entity.Menu;
import org.apache.ibatis.annotations.Select;

import java.util.List;

public interface MenuMapper extends BaseMapper<Menu> {

    @Select("SELECT m.* FROM menu m INNER JOIN role_menu rm ON m.id = rm.menu_id " +
            "WHERE rm.role = #{role} AND m.is_deleted = 0 ORDER BY m.sort_order ASC")
    List<Menu> findByRole(String role);
}
