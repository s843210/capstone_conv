import React, {useMemo, useState} from 'react';
import {SafeAreaView, Text, FlatList, View, Pressable, Alert, TextInput, StyleSheet} from 'react-native';
import {RequestItem, MyRequestsScreenProps} from '../types';
import {styles} from '../styles/commonStyles';
import {MAX_REQUEST_QTY} from '../data/appConstants';

type Props = MyRequestsScreenProps & {
  requests: RequestItem[];
  removeRequest: (requestId: string) => Promise<boolean>;
  updateRequestQty: (requestId: string, qty: number) => Promise<boolean>;
  currentUser: string;
  logoutUser: () => Promise<boolean>;
};

export default function MyRequestsScreen({
  requests,
  removeRequest,
  updateRequestQty,
  currentUser,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQty, setEditQty] = useState('');
  const [keyword, setKeyword] = useState('');

  const normalizedKeyword = keyword.trim().toLocaleLowerCase();
  const hasKeyword = normalizedKeyword.length > 0;

  const filteredRequests = useMemo(() => {
    if (!hasKeyword) {
      return requests;
    }

    return requests.filter(item => item.productName.toLocaleLowerCase().includes(normalizedKeyword));
  }, [hasKeyword, normalizedKeyword, requests]);

  const handleRemove = (requestId: string) => {
    Alert.alert('요청 삭제', '이 요청을 삭제하시겠습니까?', [
      {text: '취소', style: 'cancel'},
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          const removed = await removeRequest(requestId);
          if (!removed) {
            Alert.alert('삭제 오류', '요청 삭제 중 오류가 발생했습니다.');
          }
          if (editingId === requestId) {
            setEditingId(null);
            setEditQty('');
          }
        },
      },
    ]);
  };

  const startEdit = (item: RequestItem) => {
    setEditingId(item.id);
    setEditQty(String(item.qty));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditQty('');
  };

  const saveEdit = async (requestId: string) => {
    const trimmedQty = editQty.trim();
    if (!trimmedQty) {
      Alert.alert('입력 오류', '요청 수량을 입력해 주세요.');
      return;
    }
    if (!/^\d+$/.test(trimmedQty)) {
      Alert.alert('입력 오류', '수량은 소수점/문자 없이 정수만 입력해 주세요.');
      return;
    }

    const num = Number(trimmedQty);
    if (!Number.isInteger(num)) {
      Alert.alert('입력 오류', '수량은 정수만 입력해 주세요.');
      return;
    }
    if (num <= 0) {
      Alert.alert('입력 오류', '수량은 1개 이상 입력해 주세요.');
      return;
    }
    if (num > MAX_REQUEST_QTY) {
      Alert.alert('입력 오류', `최대 요청 수량은 ${MAX_REQUEST_QTY}개입니다.`);
      return;
    }

    const updated = await updateRequestQty(requestId, num);
    if (!updated) {
      Alert.alert('수정 오류', '요청 수량 수정 중 오류가 발생했습니다.');
      return;
    }

    cancelEdit();
  };

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.subtitle}>{currentUser}님의 요청 목록</Text>

      <View style={localStyles.searchRow}>
        <TextInput
          placeholder="요청 상품 검색"
          placeholderTextColor="#94A3B8"
          value={keyword}
          onChangeText={setKeyword}
          style={localStyles.searchInput}
        />
      </View>

      <FlatList
        data={filteredRequests}
        keyExtractor={item => item.id}
        renderItem={({item}) => {
          const isEditing = editingId === item.id;

          return (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>{item.productName}</Text>
              <Text style={styles.cardMeta}>상태: 요청 접수</Text>

              {isEditing ? (
                <>
                  <Text style={styles.cardMeta}>수량 수정</Text>
                  <TextInput
                    keyboardType="number-pad"
                    value={editQty}
                    onChangeText={setEditQty}
                    style={styles.input}
                  />
                  <View style={styles.inlineBtnRow}>
                    <Pressable style={styles.inlineSaveBtn} onPress={() => saveEdit(item.id)}>
                      <Text style={styles.inlineSaveBtnText}>저장</Text>
                    </Pressable>
                    <Pressable style={styles.inlineCancelBtn} onPress={cancelEdit}>
                      <Text style={styles.inlineCancelBtnText}>취소</Text>
                    </Pressable>
                  </View>
                </>
              ) : (
                <>
                  <Text style={styles.cardMeta}>수량: {item.qty}</Text>
                  <Text style={styles.cardMeta}>{item.createdAt}</Text>
                  <View style={styles.inlineBtnRow}>
                    <Pressable style={styles.editGhostBtn} onPress={() => startEdit(item)}>
                      <Text style={styles.editGhostBtnText}>수정</Text>
                    </Pressable>
                    <Pressable style={styles.dangerGhostBtn} onPress={() => handleRemove(item.id)}>
                      <Text style={styles.dangerGhostBtnText}>삭제</Text>
                    </Pressable>
                  </View>
                </>
              )}
            </View>
          );
        }}
        ListEmptyComponent={
          <View style={localStyles.emptyWrap}>
            {requests.length === 0 ? (
              <>
                <Text style={styles.emptyText}>아직 요청한 상품이 없어요</Text>
                <Text style={localStyles.emptySub}>상품 목록에서 필요한 상품을 요청해보세요.</Text>
              </>
            ) : hasKeyword ? (
              <>
                <Text style={styles.emptyText}>검색 결과가 없어요</Text>
                <Text style={localStyles.emptySub}>다른 상품명으로 검색해보세요.</Text>
              </>
            ) : (
              <>
                <Text style={styles.emptyText}>아직 요청한 상품이 없어요</Text>
                <Text style={localStyles.emptySub}>상품 목록에서 필요한 상품을 요청해보세요.</Text>
              </>
            )}
          </View>
        }
      />
    </SafeAreaView>
  );
}

const localStyles = StyleSheet.create({
  searchRow: {
    marginBottom: 12,
  },
  searchInput: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#111827',
    fontSize: 15,
  },
  emptyWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 32,
  },
  emptySub: {
    color: '#64748B',
    fontSize: 14,
    marginTop: 4,
  },
});
