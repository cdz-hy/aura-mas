package com.learning.service;

import com.learning.dto.MenuNode;
import com.learning.entity.Menu;
import com.learning.mapper.MenuMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class MenuService {

    private final MenuMapper menuMapper;

    public List<MenuNode> getMenuTreeByRole(String role) {
        List<Menu> flatList = menuMapper.findByRole(role);
        if (flatList.isEmpty()) {
            return Collections.emptyList();
        }

        Map<Long, MenuNode> nodeMap = new LinkedHashMap<>();
        for (Menu menu : flatList) {
            nodeMap.put(menu.getId(), MenuNode.builder()
                    .code(menu.getCode())
                    .name(menu.getName())
                    .path(menu.getPath())
                    .icon(menu.getIcon())
                    .type(menu.getType())
                    .build());
        }

        List<MenuNode> roots = new ArrayList<>();
        for (Menu menu : flatList) {
            MenuNode node = nodeMap.get(menu.getId());
            if (menu.getParentId() == null || menu.getParentId() == 0) {
                roots.add(node);
            } else {
                MenuNode parent = nodeMap.get(menu.getParentId());
                if (parent != null) {
                    parent.getChildren().add(node);
                } else {
                    roots.add(node);
                }
            }
        }

        return roots;
    }
}
