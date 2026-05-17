import React, {useMemo, useState} from 'react';
import {
  SafeAreaView,
  Text,
  FlatList,
  Pressable,
  View,
  StyleSheet,
  TextInput,
  Image,
  Alert,
} from 'react-native';
import {Suggestion, SuggestionsScreenProps} from '../types';

type Props = SuggestionsScreenProps & {
  suggestions: Suggestion[];
  currentUser: string;
  removeSuggestion: (suggestionId: string, requestUser: string) => Promise<boolean>;
  removeSuggestionsBulk: (
    suggestionIds: string[],
    requestUser: string,
  ) => Promise<{removedCount: number; failedCount: number}>;
};

type HeaderActionsProps = {
  isSelectMode: boolean;
  selectedCount: number;
  isDeleting: boolean;
  onToggleMode: () => void;
  onCreate: () => void;
  onDeleteSelected: () => void;
};

function HeaderActions({
  isSelectMode,
  selectedCount,
  isDeleting,
  onToggleMode,
  onCreate,
  onDeleteSelected,
}: HeaderActionsProps) {
  if (isSelectMode) {
    return (
      <View style={localStyles.actionRow}>
        <Pressable style={localStyles.secondaryBtn} onPress={onToggleMode}>
          <Text style={localStyles.secondaryBtnText}>취소</Text>
        </Pressable>
        <Pressable
          style={[localStyles.deleteBtn, (selectedCount === 0 || isDeleting) && localStyles.deleteBtnDisabled]}
          onPress={onDeleteSelected}
          disabled={selectedCount === 0 || isDeleting}>
          <Text style={localStyles.deleteBtnText}>삭제하기</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={localStyles.actionRow}>
      <Pressable style={localStyles.writeBtn} onPress={onCreate}>
        <Image
          source={require('../../assets/images/write-icon.png')}
          style={localStyles.writeIcon}
          resizeMode="contain"
        />
        <Text style={localStyles.writeBtnText}>작성하기</Text>
      </Pressable>
      <Pressable style={localStyles.secondaryBtn} onPress={onToggleMode}>
        <Text style={localStyles.secondaryBtnText}>선택</Text>
      </Pressable>
    </View>
  );
}

type ItemCardProps = {
  item: Suggestion;
  isSelectMode: boolean;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onOpenDetail: (item: Suggestion) => void;
};

function ItemCard({item, isSelectMode, isSelected, onToggleSelect, onOpenDetail}: ItemCardProps) {
  const handlePress = () => {
    if (isSelectMode) {
      onToggleSelect(item.id);
      return;
    }
    onOpenDetail(item);
  };

  return (
    <Pressable style={[localStyles.card, isSelectMode && isSelected && localStyles.cardSelected]} onPress={handlePress}>
      <View style={localStyles.cardRow}>
        {isSelectMode ? (
          <Pressable
            style={[
              localStyles.checkbox,
              isSelected ? localStyles.checkboxSelected : localStyles.checkboxUnselected,
            ]}
            onPress={() => onToggleSelect(item.id)}>
            {isSelected ? <Text style={localStyles.checkboxCheck}>✓</Text> : null}
          </Pressable>
        ) : null}

        <View style={localStyles.cardContent}>
          <Text style={localStyles.cardTitle}>{item.title}</Text>
          <View style={localStyles.metaRow}>
            <Text style={localStyles.metaText}>
              {item.writer} · {item.updatedAt ?? item.createdAt}
            </Text>
          </View>
        </View>
      </View>
    </Pressable>
  );
}

export default function SuggestionsScreen({
  navigation,
  suggestions,
  currentUser,
  removeSuggestion: _removeSuggestion,
  removeSuggestionsBulk,
}: Props) {
  const [keyword, setKeyword] = useState('');
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState<string[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);

  const hasKeyword = keyword.trim().length > 0;

  const filteredSuggestions = useMemo(() => {
    const q = keyword.trim();
    if (!q) {
      return suggestions;
    }
    return suggestions.filter(item => item.title.includes(q) || item.content.includes(q));
  }, [suggestions, keyword]);

  const selectedCount = selectedSuggestionIds.length;

  const toggleSelectMode = () => {
    if (isSelectMode) {
      setIsSelectMode(false);
      setSelectedSuggestionIds([]);
      return;
    }
    setIsSelectMode(true);
  };

  const toggleSuggestionSelection = (suggestionId: string) => {
    setSelectedSuggestionIds(prev =>
      prev.includes(suggestionId) ? prev.filter(id => id !== suggestionId) : [...prev, suggestionId],
    );
  };

  const confirmDeleteSelected = () => {
    if (selectedCount === 0 || isDeleting) {
      return;
    }

    Alert.alert(
      '선택한 건의사항 삭제',
      '선택한 건의사항을 삭제할까요? 삭제한 내용은 되돌릴 수 없습니다.',
      [
        {text: '취소', style: 'cancel'},
        {
          text: '삭제',
          style: 'destructive',
          onPress: async () => {
            setIsDeleting(true);
            try {
              const {removedCount, failedCount} = await removeSuggestionsBulk(selectedSuggestionIds, currentUser);

              if (removedCount === 0) {
                Alert.alert('삭제 오류', '삭제할 수 있는 건의사항이 없습니다.');
              } else if (failedCount > 0) {
                Alert.alert(
                  '일부 삭제 완료',
                  `${removedCount}개 삭제 완료, ${failedCount}개는 삭제할 수 없습니다.`,
                );
              }
            } catch {
              Alert.alert('삭제 오류', '선택한 건의사항 삭제 중 오류가 발생했습니다.');
            } finally {
              setIsDeleting(false);
              setSelectedSuggestionIds([]);
              setIsSelectMode(false);
            }
          },
        },
      ],
    );
  };

  return (
    <SafeAreaView style={localStyles.page}>
      <View style={localStyles.guideWrap}>
        <Text style={localStyles.guideText}>쿱스켓 이용 중 필요한 의견을 자유롭게 남겨보세요.</Text>
      </View>

      <View style={localStyles.searchRow}>
        <TextInput
          placeholder="건의사항 검색"
          placeholderTextColor="#94A3B8"
          value={keyword}
          onChangeText={setKeyword}
          style={localStyles.searchInput}
        />
      </View>

      <View style={localStyles.sectionHeader}>
        <Text style={localStyles.sectionTitle}>건의사항 목록</Text>
        <HeaderActions
          isSelectMode={isSelectMode}
          selectedCount={selectedCount}
          isDeleting={isDeleting}
          onToggleMode={toggleSelectMode}
          onCreate={() => navigation.navigate('SuggestionWrite')}
          onDeleteSelected={confirmDeleteSelected}
        />
      </View>

      {isSelectMode && selectedCount > 0 ? (
        <Text style={localStyles.selectedCountText}>{selectedCount}개 선택됨</Text>
      ) : null}

      <FlatList
        data={filteredSuggestions}
        keyExtractor={item => item.id}
        contentContainerStyle={localStyles.listContent}
        renderItem={({item}) => (
          <ItemCard
            item={item}
            isSelectMode={isSelectMode}
            isSelected={selectedSuggestionIds.includes(item.id)}
            onToggleSelect={toggleSuggestionSelection}
            onOpenDetail={target => navigation.navigate('SuggestionDetail', {suggestion: target})}
          />
        )}
        ListEmptyComponent={
          <View style={localStyles.emptyWrap}>
            {suggestions.length === 0 ? (
              <>
                <Text style={localStyles.emptyTitle}>아직 등록된 건의사항이 없어요</Text>
                <Text style={localStyles.emptySub}>건의사항을 작성해보세요.</Text>
              </>
            ) : hasKeyword ? (
              <>
                <Text style={localStyles.emptyTitle}>검색 결과가 없어요</Text>
                <Text style={localStyles.emptySub}>다른 검색어로 다시 검색해보세요.</Text>
              </>
            ) : (
              <>
                <Text style={localStyles.emptyTitle}>아직 등록된 건의사항이 없어요</Text>
                <Text style={localStyles.emptySub}>건의사항을 작성해보세요.</Text>
              </>
            )}
          </View>
        }
      />
    </SafeAreaView>
  );
}

const localStyles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  guideWrap: {
    marginBottom: 10,
    paddingTop: 2,
  },
  guideText: {
    color: '#64748B',
    fontSize: 15,
    lineHeight: 22,
  },
  searchRow: {
    marginBottom: 12,
  },
  searchInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#111827',
    fontSize: 15,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    gap: 10,
  },
  sectionTitle: {
    color: '#111827',
    fontSize: 22,
    fontWeight: '800',
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  secondaryBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    paddingVertical: 9,
    paddingHorizontal: 10,
    borderRadius: 10,
  },
  secondaryBtnText: {
    color: '#111827',
    fontWeight: '700',
    fontSize: 13,
  },
  writeBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    paddingVertical: 9,
    paddingHorizontal: 10,
    borderRadius: 10,
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
  },
  writeIcon: {
    width: 20,
    height: 20,
  },
  writeBtnText: {
    color: '#111827',
    fontWeight: '700',
    fontSize: 13,
  },
  deleteBtn: {
    backgroundColor: '#DC2626',
    borderWidth: 1,
    borderColor: '#DC2626',
    paddingVertical: 9,
    paddingHorizontal: 10,
    borderRadius: 10,
  },
  deleteBtnDisabled: {
    backgroundColor: '#FCA5A5',
    borderColor: '#FCA5A5',
  },
  deleteBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 13,
  },
  selectedCountText: {
    color: '#64748B',
    fontSize: 13,
    marginBottom: 10,
  },
  listContent: {
    paddingBottom: 12,
    flexGrow: 1,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#0F172A',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: {width: 0, height: 4},
    elevation: 1,
  },
  cardSelected: {
    borderColor: '#0060AF',
    backgroundColor: '#EFF6FF',
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  checkboxUnselected: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#CBD5E1',
  },
  checkboxSelected: {
    backgroundColor: '#0060AF',
    borderWidth: 1,
    borderColor: '#0060AF',
  },
  checkboxCheck: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 14,
  },
  cardContent: {
    flex: 1,
  },
  cardTitle: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 8,
  },
  metaRow: {
    alignItems: 'flex-start',
  },
  metaText: {
    color: '#94A3B8',
    fontSize: 12,
  },
  emptyWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 44,
  },
  emptyTitle: {
    color: '#334155',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 6,
  },
  emptySub: {
    color: '#64748B',
    fontSize: 14,
  },
});
